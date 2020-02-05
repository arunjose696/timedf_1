import pandas as pd
import subprocess
import time
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from server import OmnisciServer
import ibis

class OmnisciServerWorker:
    _imported_pd_df = {}

    def __init__(self, omnisci_server):
        self.omnisci_server = omnisci_server
        self._omnisci_cmd_line = [self.omnisci_server.omnisci_sql_executable] \
                                 + [str(self.omnisci_server.database_name),
                                    "-u", self.omnisci_server.user,
                                    "-p", self.omnisci_server.password] \
                                 + ["--port", str(self.omnisci_server.server_port)]
        self._command_2_import_CSV = "COPY %s FROM '%s' WITH (header='%s');"
        self._conn = None

    def _read_csv_datafile(self, file_name, columns_names, header=None, compression_type='gzip',
                           nrows=200000):
        "Read csv by Pandas. Function returns Pandas DataFrame,\
        which can be used by ibis load_data function"

        print("Reading datafile", file_name)
        return pd.read_csv(file_name, compression=compression_type, header=header,
                           names=columns_names, nrows=nrows)

    def connect_to_server(self):
        "Connect to Omnisci server using Ibis framework"

        self._conn = ibis.omniscidb.connect(host="localhost", port=self.omnisci_server.server_port,
                                            user=self.omnisci_server.user,
                                            password=self.omnisci_server.password)
        return self._conn

    def terminate(self):
        self.omnisci_server.terminate()

    def import_data(self, table_name, data_files_names, files_limit, columns_names, columns_types,
                    header=False):
        "Import CSV files using COPY SQL statement"

        if header:
            header_value = 'true'
        elif not header:
            header_value = 'false'
        else:
            print("Wrong value of header argument!")
            sys.exit(2)

        schema_table = ibis.Schema(
            names=columns_names,
            types=columns_types
        )

        if not self._conn.exists_table(name=table_name, database=self.omnisci_server.database_name):
            try:
                self._conn.create_table(table_name=table_name, schema=schema_table,
                                        database=self.omnisci_server.database_name)
            except Exception as err:
                print("Failed to create table:", err)

        for f in data_files_names[:files_limit]:
            print("Importing datafile", f)
            copy_str = self._command_2_import_CSV % (table_name, f, header_value)

            try:
                import_process = subprocess.Popen(self._omnisci_cmd_line, stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                output = import_process.communicate(copy_str.encode())
            except OSError as err:
                print("Failed to start", self._omnisci_cmd_line, err)

            print(str(output[0].strip().decode()))
            print("Command returned", import_process.returncode)

    def import_data_by_ibis(self, table_name, data_files_names, files_limit, columns_names,
                            columns_types, cast_dict, header=None):
        "Import CSV files using Ibis load_data from the Pandas.DataFrame"

        schema_table = ibis.Schema(
            names=columns_names,
            types=columns_types
        )

        if not self._conn.exists_table(name=table_name, database=self.omnisci_server.database_name):
            try:
                self._conn.create_table(table_name=table_name, schema=schema_table,
                                        database=self.omnisci_server.database_name)
            except Exception as err:
                print("Failed to create table:", err)

        t0 = time.time()
        if files_limit > 1:
            pandas_df_from_each_file = (self._read_csv_datafile(file_name, columns_names, header)
                                        for file_name in data_files_names[:files_limit])
            self._imported_pd_df[table_name] = pd.concat(pandas_df_from_each_file,
                                                         ignore_index=True)
        else:
            self._imported_pd_df[table_name] = self._read_csv_datafile(data_files_names,
                                                                       columns_names, header)

        t_import_pandas = time.time() - t0

        pandas_concatenated_df_casted = self._imported_pd_df[table_name].astype(dtype=cast_dict,
                                                                                copy=True)

        t0 = time.time()
        self._conn.load_data(table_name=table_name, obj=pandas_concatenated_df_casted,
                             database=self.omnisci_server.database_name)
        t_import_ibis = time.time() - t0

        return t_import_pandas, t_import_ibis

    def drop_table(self, table_name):
        "Drop table by table_name using Ibis framework"

        if self._conn.exists_table(name=table_name, database=self.omnisci_server.database_name):
            db = self._conn.database(self.omnisci_server.database_name)
            df = db.table(table_name)
            df.drop()
            if table_name in self._imported_pd_df:
                del self._imported_pd_df[table_name]
        else:
            print("Table", table_name, "doesn't exist!")
            sys.exit(3)

    def get_pd_df(self, table_name):
        "Get already imported Pandas DataFrame"

        if self._conn.exists_table(name=table_name, database=self.omnisci_server.database_name):
            return self._imported_pd_df[table_name]
        else:
            print("Table", table_name, "doesn't exist!")
            sys.exit(4)