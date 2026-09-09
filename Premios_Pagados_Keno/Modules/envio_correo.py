import smtplib
import ssl
from contextlib import closing
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import pyodbc
from Modules.credentials import construir_conexion_sql, consultar


class EnvioCorreo:
    """Notifica el resultado exitoso usando las credenciales de sp_getData."""

    FIRMA_PATH = Path(__file__).resolve().parent / "Assets" / "Firma.jpg"

    _consultar = staticmethod(consultar)

    def enviar(self, destinatarios: list[str]) -> None:
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
        mensaje["Subject"] = "Premios Pagados Keno - Ejecucion correcta"
        mensaje["From"] = str(usuario)
        mensaje["To"] = ", ".join(destinatarios)
        cuerpo = "El flujo de Premios Pagados Keno se ejecuto correctamente y los reportes se subieron al SFTP."
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
        print("[INFO] Correo de ejecucion correcta enviado.")
