"""
Parser para el archivo de Excel Estándar COMTRADE.
Extrae bloques de señales y nombres de señales para modelos de relés específicos.
"""
import pandas as pd
import os
from typing import Dict, List, Optional

class ExcelStandardParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo Excel no encontrado: {file_path}")

    def get_available_models(self) -> List[str]:
        """Retorna los nombres de las hojas (modelos de relés) disponibles."""
        xl = pd.ExcelFile(self.file_path)
        return xl.sheet_names

    def parse_sheet(self, sheet_name: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Parsea una hoja específica y extrae los bloques de señales.
        Retorna un diccionario: { 'NombreBloque': [{'name': 'NombreSeñal', 'group': 'Y/N'}] }
        """
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None)
        except Exception as e:
            print(f"Error al leer hoja {sheet_name}: {e}")
            return {}

        blocks = {}
        
        # Buscar bloques en la primera fila (los nombres de bloques como B1RBDR, B2RBDR, etc.)
        for col_idx in range(df.shape[1]):
            # Revisar las primeras filas para encontrar el nombre del bloque
            block_name = None
            for row_idx in range(min(5, df.shape[0])):
                cell_value = str(df.iloc[row_idx, col_idx])
                if "RBDR" in cell_value.upper() or "RADR" in cell_value.upper():
                    block_name = cell_value.strip()
                    break
            
            if not block_name:
                continue
            
            # Buscar la fila que contiene "SEÑAL" para saber dónde empiezan los datos
            signal_col_idx = None
            group_col_idx = None
            start_row = None
            
            for row_idx in range(min(10, df.shape[0])):
                # Buscar "V", "SEÑAL", "G" en las columnas cercanas
                if col_idx + 1 < df.shape[1]:
                    val = str(df.iloc[row_idx, col_idx + 1])
                    if "SEÑAL" in val.upper() or "SENAL" in val.upper():
                        signal_col_idx = col_idx + 1
                        group_col_idx = col_idx + 2 if col_idx + 2 < df.shape[1] else None
                        start_row = row_idx + 1
                        break
            
            if signal_col_idx is None or start_row is None:
                continue
            
            # Extraer las señales
            signals = []
            for row_idx in range(start_row, df.shape[0]):
                if signal_col_idx >= df.shape[1]:
                    break
                    
                signal_name = df.iloc[row_idx, signal_col_idx]
                
                # Detener si encontramos una celda vacía o otro bloque
                if pd.isna(signal_name) or signal_name == "":
                    break
                    
                signal_name_str = str(signal_name).strip()
                if "RBDR" in signal_name_str.upper() or "RADR" in signal_name_str.upper():
                    break  # Nuevo bloque encontrado
                
                group_val = ""
                if group_col_idx and group_col_idx < df.shape[1]:
                    group_val = str(df.iloc[row_idx, group_col_idx]) if not pd.isna(df.iloc[row_idx, group_col_idx]) else ""
                
                signals.append({
                    "name": signal_name_str,
                    "description": "",
                    "group": group_val.strip()
                })
            
            if signals:
                blocks[block_name] = signals
        
        if blocks:
            return blocks

        # Estrategia 2: formato por tablas funcionales (Señal/Descripción/Arranca)
        header_row = None
        for row_idx in range(min(20, df.shape[0])):
            row_texts = [str(df.iloc[row_idx, c]).strip().upper()
                         for c in range(df.shape[1])
                         if not pd.isna(df.iloc[row_idx, c]) and str(df.iloc[row_idx, c]).strip()]
            if any(txt in ["SEÑAL", "SENAL"] for txt in row_texts):
                header_row = row_idx
                break

        if header_row is None:
            return {}

        for col_idx in range(df.shape[1]):
            cell = df.iloc[header_row, col_idx]
            if pd.isna(cell):
                continue

            header_txt = str(cell).strip().upper()
            if header_txt not in ["SEÑAL", "SENAL"]:
                continue

            desc_col = col_idx + 1 if (col_idx + 1) < df.shape[1] else None
            group_col = col_idx + 2 if (col_idx + 2) < df.shape[1] else None

            block_name = ""
            for up in range(header_row - 1, -1, -1):
                up_cell = df.iloc[up, col_idx]
                if not pd.isna(up_cell) and str(up_cell).strip():
                    block_name = str(up_cell).strip()
                    break

            if not block_name:
                block_name = f"TABLA_{col_idx + 1}"

            signals = []
            for row_idx in range(header_row + 1, df.shape[0]):
                sig_val = df.iloc[row_idx, col_idx]
                if pd.isna(sig_val) or str(sig_val).strip() == "":
                    break

                sig_name = str(sig_val).strip()
                sig_desc = ""
                sig_group = ""

                if desc_col is not None:
                    d_val = df.iloc[row_idx, desc_col]
                    if not pd.isna(d_val):
                        sig_desc = str(d_val).strip()

                if group_col is not None:
                    g_val = df.iloc[row_idx, group_col]
                    if not pd.isna(g_val):
                        sig_group = str(g_val).strip()

                signals.append({
                    "name": sig_name,
                    "description": sig_desc,
                    "group": sig_group
                })

            if signals:
                base_name = block_name
                suffix = 2
                while block_name in blocks:
                    block_name = f"{base_name} ({suffix})"
                    suffix += 1
                blocks[block_name] = signals

        return blocks

    def parse_all_sheets(self) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """Parsea todas las hojas del archivo y retorna su estructura por bloques."""
        all_data: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        for sheet_name in self.get_available_models():
            all_data[sheet_name] = self.parse_sheet(sheet_name)
        return all_data

    def save_sheet_blocks(self, sheet_name: str,
                         blocks: Dict[str, List[Dict[str, str]]]):
        """Sobrescribe una hoja del Excel con bloques normalizados (CRUD)."""
        # Leer todas las hojas existentes para preservar el libro completo
        all_sheets = pd.read_excel(self.file_path, sheet_name=None, header=None)

        # Construir la hoja destino con el formato esperado por parse_sheet
        all_sheets[sheet_name] = self._build_sheet_dataframe(blocks)

        # Escribir nuevamente el libro con todas las hojas
        with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
            for name, df in all_sheets.items():
                # Evitar escritura de índices/headers de pandas
                df.to_excel(writer, sheet_name=name, index=False, header=False)

    def save_all_sheets(self, all_data: Dict[str, Dict[str, List[Dict[str, str]]]]):
        """Sobrescribe todas las hojas del archivo con la estructura CRUD en memoria."""
        if not all_data:
            raise ValueError("No hay datos para guardar en el XLSX")

        with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
            for sheet_name, blocks in all_data.items():
                df = self._build_sheet_dataframe(blocks)
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)

    def _build_sheet_dataframe(self, blocks: Dict[str, List[Dict[str, str]]]) -> pd.DataFrame:
        """Crea un DataFrame con layout de bloques para persistir en XLSX."""
        if not blocks:
            return pd.DataFrame([[]])

        max_signals = max((len(signals) for signals in blocks.values()), default=0)
        total_rows = max(3, max_signals + 3)  # título + header + datos

        # Cada bloque ocupa 3 columnas + 1 separación
        total_cols = (len(blocks) * 4) - 1
        matrix = [["" for _ in range(total_cols)] for _ in range(total_rows)]

        base_col = 0
        for block_name, signals in blocks.items():
            matrix[0][base_col] = block_name
            matrix[1][base_col] = "Señal"
            matrix[1][base_col + 1] = "Descripción"
            matrix[1][base_col + 2] = "Arranca"

            for row_idx, sig in enumerate(signals, start=2):
                matrix[row_idx][base_col] = (sig.get('name') or '').strip()
                matrix[row_idx][base_col + 1] = (sig.get('description') or '').strip()
                matrix[row_idx][base_col + 2] = (sig.get('group') or '').strip()

            base_col += 4

        return pd.DataFrame(matrix)

if __name__ == "__main__":
    # Test rápido
    parser = ExcelStandardParser("Estándar COMTRADE.xlsx")
    models = parser.get_available_models()
    print(f"Modelos disponibles: {models}")
    if "REC670" in models:
        data = parser.parse_sheet("REC670")
        for b, sigs in data.items():
            print(f"Bloque: {b} - {len(sigs)} señales")
            for s in sigs[:3]:
                print(f"  - {s}")
