import importlib.util
from datetime import date
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
import pyodbc
from unittest.mock import MagicMock, patch


PROJECT = Path(__file__).resolve().parents[1] / "Premios_Pagados_Keno"
sys.path.insert(0, str(PROJECT))
from Modules.envio_correo import EnvioCorreo


class CorreoTests(unittest.TestCase):
    def ejecutar_envio(self, puerto=587, firma=None, rechazados=None):
        cursor = MagicMock(spec_set=pyodbc.Cursor)
        cursor.description = [(name,) for name in
                              ("port_smtp", "server_smtp", "pass_smtp", "user_smtp")]
        cursor.fetchone.side_effect = [
            (puerto, "smtp.example.test", None, None),
            (None, None, "password-test", "robot@example.test"),
        ]
        conexion = MagicMock(spec_set=pyodbc.Connection)
        conexion.cursor.return_value = cursor
        with patch("Modules.envio_correo.construir_conexion_sql", return_value="conexion-test"), \
             patch("Modules.envio_correo.pyodbc.connect", return_value=conexion), \
             patch("Modules.envio_correo.smtplib.SMTP") as smtp, \
             patch("Modules.envio_correo.smtplib.SMTP_SSL") as smtp_ssl, \
             patch.object(EnvioCorreo, "FIRMA_PATH", firma):
            servidor = (smtp_ssl if puerto == 465 else smtp).return_value
            servidor.send_message.return_value = rechazados or {}
            EnvioCorreo().enviar(["destino@example.test"], date(2026, 12, 31))
            mensaje = servidor.send_message.call_args.args[0]
        self.assertEqual(cursor.execute.call_args_list[0].args, ("EXEC sp_getData ?", "1"))
        self.assertEqual(cursor.execute.call_args_list[1].args, ("EXEC sp_getData ?", "2"))
        servidor.login.assert_called_once_with("robot@example.test", "password-test")
        cursor.close.assert_called_once()
        conexion.close.assert_called_once()
        self.assertEqual(conexion.timeout, 30)
        return servidor, mensaje

    def test_starttls_sin_firma(self):
        with tempfile.TemporaryDirectory() as carpeta:
            servidor, mensaje = self.ejecutar_envio(firma=Path(carpeta) / "ausente.png")
        servidor.starttls.assert_called_once()
        self.assertEqual(mensaje["To"], "destino@example.test")
        self.assertEqual(mensaje["Subject"], "Premios Pagados Keno - Mes procesado: diciembre de 2026")
        for formato in ("plain", "html"):
            self.assertIn("ya se proceso el mes de diciembre de 2026",
                          mensaje.get_body(preferencelist=(formato,)).get_content())
        self.assertIn("correctamente", mensaje.get_body(preferencelist=("plain",)).get_content())

    def test_tls_directo_con_firma_cid(self):
        with tempfile.TemporaryDirectory() as carpeta:
            firma = Path(carpeta) / "Firma.jpg"
            firma.write_bytes(b"imagen-test")
            servidor, mensaje = self.ejecutar_envio(puerto=465, firma=firma)
        servidor.starttls.assert_not_called()
        imagen = next(part for part in mensaje.walk() if part.get_content_type() == "image/jpeg")
        self.assertIn(imagen["Content-ID"][1:-1], mensaje.get_body(preferencelist=("html",)).get_content())
        self.assertEqual(imagen.get_content_disposition(), "inline")

    def test_destinatarios_vacios_no_conectan(self):
        with patch("Modules.envio_correo.pyodbc.connect") as conectar:
            with self.assertRaises(ValueError):
                EnvioCorreo().enviar([], date(2026, 12, 31))
        conectar.assert_not_called()

    def test_credenciales_incompletas(self):
        cursor = MagicMock()
        cursor.description = [("server_smtp",), ("port_smtp",)]
        cursor.fetchone.return_value = (None, 587)
        with self.assertRaises(RuntimeError):
            EnvioCorreo._consultar(cursor, "1", ("server_smtp", "port_smtp"))

    def test_rechazo_destinatario_es_error(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaisesRegex(RuntimeError, "rechazo"):
                self.ejecutar_envio(firma=Path(carpeta) / "ausente.png",
                                   rechazados={"destino@example.test": (550, b"Rejected")})

    def test_fallo_flujo_no_envia_correo(self):
        navegacion = types.ModuleType("web.navigation")
        navegacion.navigation = MagicMock(side_effect=RuntimeError("Fallo descarga"))
        with patch.dict(sys.modules, {"web.navigation": navegacion}):
            spec = importlib.util.spec_from_file_location("keno_main_test", PROJECT / "main.py")
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        with patch.object(modulo, "EnvioCorreo") as correo:
            with self.assertRaisesRegex(RuntimeError, "Fallo descarga"):
                modulo.main()
        correo.assert_not_called()

    def test_dias_distintos_del_primero_no_envian_ni_conectan(self):
        with patch.object(EnvioCorreo, "enviar") as enviar, \
             patch("Modules.envio_correo.pyodbc.connect") as conectar:
            for dia in (2, 11, 30):
                self.assertFalse(EnvioCorreo().enviar_si_corresponde(
                    ["destino@example.test"], date(2026, 9, dia)))
        enviar.assert_not_called()
        conectar.assert_not_called()

    def test_primer_dia_notifica_mes_anterior_una_sola_vez(self):
        with tempfile.TemporaryDirectory() as carpeta, \
             patch.object(EnvioCorreo, "ESTADO_DIR", Path(carpeta)), \
             patch.object(EnvioCorreo, "enviar") as enviar:
            for inicio, corte in ((date(2027, 1, 1), date(2026, 12, 31)),
                                  (date(2027, 2, 1), date(2027, 1, 31)),
                                  (date(2028, 3, 1), date(2028, 2, 29))):
                with self.subTest(inicio=inicio):
                    self.assertTrue(EnvioCorreo().enviar_si_corresponde(
                        ["destino@example.test"], inicio))
                    enviar.assert_called_with(["destino@example.test"], corte)
                    self.assertTrue((Path(carpeta) / f"{corte:%Y-%m}.enviado").exists())
                    self.assertFalse(EnvioCorreo().enviar_si_corresponde(
                        ["destino@example.test"], inicio))
            self.assertEqual(enviar.call_count, 3)

    def test_envio_fallido_permite_reintentar(self):
        with tempfile.TemporaryDirectory() as carpeta, \
             patch.object(EnvioCorreo, "ESTADO_DIR", Path(carpeta)), \
             patch.object(EnvioCorreo, "enviar", side_effect=[RuntimeError("SMTP"), None]) as enviar:
            with self.assertRaisesRegex(RuntimeError, "SMTP"):
                EnvioCorreo().enviar_si_corresponde(["destino@example.test"], date(2026, 10, 1))
            self.assertFalse((Path(carpeta) / "2026-09.enviado").exists())
            self.assertTrue(EnvioCorreo().enviar_si_corresponde(
                ["destino@example.test"], date(2026, 10, 1)))
            self.assertEqual(enviar.call_count, 2)


if __name__ == "__main__":
    unittest.main()
