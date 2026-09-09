import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Premios_Pagados_Keno"))
from Modules.credentials import cargar_credenciales, construir_conexion_sql, consultar, describir_error_sql
import pyodbc


class CredentialsTests(unittest.TestCase):
    def cargar(self, puerto="2222", web_password=" clave web "):
        cursor = MagicMock(spec_set=pyodbc.Cursor)
        cursor.description = [(name,) for name in (
            "PASS_SIG", "SECRET_ID", "PORT_SMTP", "TENANT_ID", "USER_SIG", "SERVER_SMTP",
        )]
        cursor.fetchone.side_effect = [
            (None, "/dashboard/31", web_password, "https://web.test", None, "web-user"),
            ("sftp-pass", None, puerto, "sftp.test", "sftp-user", None),
        ]
        conexion = MagicMock(spec_set=pyodbc.Connection)
        conexion.cursor.return_value = cursor
        with patch("Modules.credentials.construir_conexion_sql", return_value="sql-test"), \
             patch("Modules.credentials.pyodbc.connect", return_value=conexion) as conectar:
            try:
                cargar_credenciales()
            finally:
                cursor.close.assert_called_once()
                conexion.close.assert_called_once()
        conectar.assert_called_once_with("sql-test", timeout=30)
        self.assertEqual(conexion.timeout, 30)
        self.assertEqual(cursor.execute.call_args_list, [
            call("EXEC sp_getData ?", "31"), call("EXEC sp_getData ?", "29"),
        ])

    def test_mapeo_por_nombre_y_reemplazo_en_cada_ejecucion(self):
        with patch.dict(os.environ, {"WEB_URL": "anterior"}, clear=True):
            self.cargar()
            self.assertEqual(dict(os.environ), {
                "WEB_URL": "https://web.test", "WEB_USERNAME": "web-user",
                "WEB_PASSWORD": " clave web ", "DASHBOARD_URL": "https://web.test/dashboard/31",
                "SFTP_HOST": "sftp.test", "SFTP_PORT": "2222",
                "SFTP_USERNAME": "sftp-user", "SFTP_PASSWORD": "sftp-pass",
            })
            self.cargar(web_password="nueva")
            self.assertEqual(os.environ["WEB_PASSWORD"], "nueva")

    def test_puerto_invalido_no_actualiza_entorno(self):
        for puerto in ("no-numero", 0, 65536, "22.5"):
            with self.subTest(puerto=puerto), patch.dict(os.environ, {"WEB_URL": "anterior"}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "puerto SFTP invalido"):
                    self.cargar(puerto=puerto)
                self.assertEqual(dict(os.environ), {"WEB_URL": "anterior"})

    def test_campos_vacios_no_actualizan_entorno(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "incompletas"):
                self.cargar(web_password=None)
            self.assertEqual(dict(os.environ), {})

    def test_resultado_vacio_o_columna_ausente(self):
        for descripcion, fila in (([("tenant_id",)], None), ([("otro",)], ("valor",))):
            cursor = MagicMock(description=descripcion)
            cursor.fetchone.return_value = fila
            with self.assertRaisesRegex(RuntimeError, "columnas requeridas"):
                consultar(cursor, "31", ("tenant_id",))

    def test_salta_resultados_sin_columnas(self):
        cursor = MagicMock(description=None)
        def siguiente():
            cursor.description = [("tenant_id",)]
            return True
        cursor.nextset.side_effect = siguiente
        cursor.fetchone.return_value = ("web.test",)
        self.assertEqual(consultar(cursor, "31", ("tenant_id",)), ("web.test",))

    def test_sin_resultados(self):
        cursor = MagicMock(description=None)
        cursor.nextset.return_value = False
        with self.assertRaisesRegex(RuntimeError, "no devolvio resultados"):
            consultar(cursor, "29", ("tenant_id",))

    def test_error_sql_no_expone_detalles(self):
        with patch("Modules.credentials.construir_conexion_sql", return_value="sql-test"), \
             patch("Modules.credentials.pyodbc.connect", side_effect=pyodbc.Error("secreto")):
            with self.assertRaisesRegex(RuntimeError, "desde SQL Server") as error:
                cargar_credenciales()
            self.assertNotIn("secreto", str(error.exception))
            self.assertTrue(error.exception.__suppress_context__)

    def test_variables_sql_y_escape_odbc(self):
        for version in ("18", "17"):
            driver = f"ODBC Driver {version} for SQL Server"
            with patch.dict(os.environ, {
                "SERVER": "sql.test", "DATABASE": "keno", "USR": "robot", "PASS": " p;a}ss ",
            }, clear=True), patch("Modules.credentials.pyodbc.drivers", return_value=[driver]):
                self.assertEqual(construir_conexion_sql(),
                    f"DRIVER={{{driver}}};SERVER={{sql.test}};DATABASE={{keno}};"
                    "UID={robot};PWD={ p;a}}ss };Encrypt=yes;TrustServerCertificate=yes;")

    def test_variables_sql_obligatorias(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SERVER, DATABASE, USR, PASS"):
                construir_conexion_sql()

    def test_confia_en_certificado_y_mantiene_cifrado(self):
        with patch.dict(os.environ, {
            **dict.fromkeys(("SERVER", "DATABASE", "USR", "PASS"), "test"),
        }, clear=True), patch("Modules.credentials.pyodbc.drivers", return_value=["ODBC Driver 17 for SQL Server"]):
            self.assertIn("Encrypt=yes;TrustServerCertificate=yes;", construir_conexion_sql())

    def test_diagnostico_certificado_sin_secretos(self):
        error = pyodbc.Error("08001", "SSL Provider: cadena de certificacion no confiable (-2146893019) usuario-secreto")
        mensaje = describir_error_sql(error)
        self.assertIn("SQLSTATE 08001", mensaje)
        self.assertIn("infraestructura", mensaje)
        self.assertNotIn("usuario-secreto", mensaje)

    def test_driver_ausente(self):
        with patch.dict(os.environ, dict.fromkeys(("SERVER", "DATABASE", "USR", "PASS"), "test")), \
             patch("Modules.credentials.pyodbc.drivers", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "Instale ODBC"):
                construir_conexion_sql()


if __name__ == "__main__":
    unittest.main()
