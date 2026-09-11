import smtplib
import ssl
from contextlib import closing
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import pyodbc
from Modules.credentials import construir_conexion_sql, consultar


class EnvioCorreo:
    """Notifica el resultado exitoso usando las credenciales de sp_getData."""

    FIRMA_PATH = Path(__file__).resolve().parent / "Assets" / "Firma.jpg"
    ESTADO_DIR = Path(__file__).resolve().parents[1] / ".estado_correo"
    MESES = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )

    _consultar = staticmethod(consultar)

    def enviar_si_corresponde(self, destinatarios: list[str], fecha_ejecucion: date) -> bool:
        """Notifica el mes anterior solo el dia 1, tras un flujo exitoso."""
        if fecha_ejecucion.day != 1:
            print("[INFO] Hoy no corresponde enviar el correo mensual.")
            return False

        fecha_corte = fecha_ejecucion - timedelta(days=1)
        self.ESTADO_DIR.mkdir(parents=True, exist_ok=True)
        registro = self.ESTADO_DIR / f"{fecha_corte:%Y-%m}.enviado"
        if registro.exists():
            print("[INFO] El correo de este mes ya fue enviado.")
            return False

        self.enviar(destinatarios, fecha_corte)
        registro.write_text(fecha_ejecucion.isoformat(), encoding="utf-8")
        return True

    def enviar(self, destinatarios: list[str], fecha_corte: date) -> None:
        if not destinatarios or any(not direccion.strip() for direccion in destinatarios):
            raise ValueError("Configure los destinatarios del correo en main.py.")
        conexion_sql = construir_conexion_sql()

        with closing(pyodbc.connect(conexion_sql, timeout=30)) as conexion:
            conexion.timeout = 30
            with closing(conexion.cursor()) as cursor:
                servidor, puerto = self._consultar(cursor, "1", ("server_smtp", "port_smtp"))
                usuario, contrasena = self._consultar(cursor, "2", ("user_smtp", "pass_smtp"))

        puerto = int(puerto)
        mensaje = EmailMessage()
        periodo = f"{self.MESES[fecha_corte.month - 1]} de {fecha_corte.year}"
        mensaje["Subject"] = f"Premios Pagados Keno - Mes procesado: {periodo}"
        mensaje["From"] = str(usuario)
        mensaje["To"] = ", ".join(destinatarios)
        cuerpo = (
            f"Se informa que ya se proceso el mes de {periodo}. "
            "El flujo de Premios Pagados Keno se ejecuto correctamente "
            "y los reportes se subieron al SFTP."
        )
        mensaje.set_content(cuerpo)
        html = f"<html><body><p>{cuerpo}</p><p>Saludos,<br>Automatizacion Premios Pagados Keno</p>"
        firma = self.FIRMA_PATH.read_bytes() if self.FIRMA_PATH.is_file() else None
        if firma:
            cid = make_msgid()
            html += f'<img src="cid:{cid[1:-1]}" alt="Firma" style="max-width:600px;">'
        else:
            print(f"[AVISO] No se encontro la firma. Agregue la imagen en: {self.FIRMA_PATH}")
        mensaje.add_alternative(html + "</body></html>", subtype="html")
        if firma:
            mensaje.get_payload()[-1].add_related(
                firma, maintype="image", subtype="jpeg", cid=cid,
                disposition="inline", filename=self.FIRMA_PATH.name,
            )

        contexto = ssl.create_default_context()
        if puerto == 465:
            smtp = smtplib.SMTP_SSL(str(servidor), puerto, timeout=30, context=contexto)
        else:
            smtp = smtplib.SMTP(str(servidor), puerto, timeout=30)
        with smtp:
            if puerto != 465:
                smtp.starttls(context=contexto)
            smtp.login(str(usuario), str(contrasena))
            rechazados = smtp.send_message(mensaje)
            if rechazados:
                raise RuntimeError("El servidor SMTP rechazo uno o mas destinatarios.")
        print(f"[INFO] Correo mensual de {periodo} enviado.")
