"""
Parser para archivos IEEE C37.111 COMTRADE (.cfg y .dat).
Soporta las revisiones 1991, 1999 y 2013.
"""
import os
import re
from typing import Optional, Tuple
from models.signal_models import (
    ComtradeConfig, ComtradeChannel, SignalType
)


class ComtradeParser:
    """Parser para pares de archivos COMTRADE .cfg/.dat."""

    def __init__(self):
        self._config: Optional[ComtradeConfig] = None

    def parse_cfg(self, cfg_path: str) -> ComtradeConfig:
        """
        Parsea un archivo .cfg COMTRADE.

        Args:
            cfg_path: Ruta al archivo .cfg

        Returns:
            ComtradeConfig con la configuración completa
        """
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"Archivo .cfg no encontrado: {cfg_path}")

        config = ComtradeConfig(file_path=cfg_path)

        with open(cfg_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = [line.strip() for line in f.readlines()]

        if len(lines) < 2:
            raise ValueError("Archivo .cfg demasiado corto")

        line_idx = 0

        # --- Línea 1: station_name, rec_dev_id, rev_year ---
        parts = self._split_cfg_line(lines[line_idx])
        config.station_name = parts[0] if len(parts) > 0 else ""
        config.rec_dev_id = parts[1] if len(parts) > 1 else ""
        if len(parts) > 2:
            try:
                config.rev_year = int(parts[2])
            except ValueError:
                config.rev_year = 1999
        line_idx += 1

        # --- Línea 2: TT, ##A, ##D ---
        parts = self._split_cfg_line(lines[line_idx])
        if len(parts) >= 1:
            total = parts[0]
            # Extraer números de canales
            num_a = 0
            num_d = 0
            for p in parts[1:]:
                p = p.strip()
                if p.upper().endswith('A'):
                    try:
                        num_a = int(p[:-1])
                    except ValueError:
                        pass
                elif p.upper().endswith('D'):
                    try:
                        num_d = int(p[:-1])
                    except ValueError:
                        pass
            # Alternativa: si solo hay un campo TT
            if num_a == 0 and num_d == 0 and len(parts) == 1:
                try:
                    tt = int(total)
                    num_a = tt  # Asumir todos analógicos
                except ValueError:
                    pass

            config.num_analog = num_a
            config.num_digital = num_d
        line_idx += 1

        # --- Canales analógicos ---
        for i in range(config.num_analog):
            if line_idx >= len(lines):
                break
            ch = self._parse_analog_channel(lines[line_idx], i + 1)
            config.analog_channels.append(ch)
            line_idx += 1

        # --- Canales digitales ---
        for i in range(config.num_digital):
            if line_idx >= len(lines):
                break
            ch = self._parse_digital_channel(lines[line_idx], i + 1)
            config.digital_channels.append(ch)
            line_idx += 1

        # --- Frecuencia de línea ---
        if line_idx < len(lines):
            try:
                config.line_freq = float(lines[line_idx])
            except ValueError:
                config.line_freq = 60.0
            line_idx += 1

        # --- Número de tasas de muestreo ---
        num_rates = 0
        if line_idx < len(lines):
            try:
                num_rates = int(lines[line_idx])
            except ValueError:
                num_rates = 0
            line_idx += 1

        # --- Tasas de muestreo ---
        for _ in range(max(num_rates, 1)):
            if line_idx >= len(lines):
                break
            parts = self._split_cfg_line(lines[line_idx])
            if len(parts) >= 2:
                try:
                    rate = float(parts[0])
                    end_sample = int(parts[1])
                    config.sampling_rates.append((rate, end_sample))
                except ValueError:
                    pass
            line_idx += 1

        # --- Timestamps ---
        if line_idx < len(lines):
            config.start_timestamp = lines[line_idx]
            line_idx += 1
        if line_idx < len(lines):
            config.trigger_timestamp = lines[line_idx]
            line_idx += 1

        # --- Formato de datos ---
        if line_idx < len(lines):
            fmt = lines[line_idx].upper().strip()
            config.data_format = fmt if fmt in ('ASCII', 'BINARY',
                                                  'BINARY32', 'FLOAT32') \
                else 'ASCII'
            line_idx += 1

        # --- Multiplicador de tiempo ---
        if line_idx < len(lines):
            try:
                config.time_multiplier = float(lines[line_idx])
            except ValueError:
                config.time_multiplier = 1.0

        self._config = config
        return config

    def _split_cfg_line(self, line: str) -> list:
        """Divide una línea .cfg por comas, respetando espacios."""
        return [p.strip() for p in line.split(',')]

    def _parse_analog_channel(self, line: str, default_idx: int) -> ComtradeChannel:
        """
        Parsea una línea de canal analógico del .cfg.
        Formato: An, ch_id, ph, ccbm, uu, a, b, skew, min, max, primary,
                 secondary, PS
        """
        ch = ComtradeChannel(signal_type=SignalType.ANALOG)
        parts = self._split_cfg_line(line)

        try:
            ch.index = int(parts[0]) if len(parts) > 0 else default_idx
        except ValueError:
            ch.index = default_idx

        ch.name = parts[1] if len(parts) > 1 else f"A{default_idx}"
        ch.phase = parts[2] if len(parts) > 2 else ""
        ch.circuit_component = parts[3] if len(parts) > 3 else ""
        ch.unit = parts[4] if len(parts) > 4 else ""

        # Valores numéricos
        float_fields = [
            (5, 'multiplier', 1.0), (6, 'offset', 0.0),
            (7, 'skew', 0.0), (8, 'min_val', -99999.0),
            (9, 'max_val', 99999.0), (10, 'primary', 1.0),
            (11, 'secondary', 1.0)
        ]
        for idx, field, default in float_fields:
            if len(parts) > idx:
                try:
                    setattr(ch, field, float(parts[idx]))
                except ValueError:
                    setattr(ch, field, default)

        ch.ps_type = parts[12].strip() if len(parts) > 12 else "P"

        return ch

    def _parse_digital_channel(self, line: str,
                                default_idx: int) -> ComtradeChannel:
        """
        Parsea una línea de canal digital del .cfg.
        Formato: Dn, ch_id, ph, ccbm, y
        """
        ch = ComtradeChannel(signal_type=SignalType.BINARY)
        parts = self._split_cfg_line(line)

        try:
            ch.index = int(parts[0]) if len(parts) > 0 else default_idx
        except ValueError:
            ch.index = default_idx

        ch.name = parts[1] if len(parts) > 1 else f"D{default_idx}"
        ch.phase = parts[2] if len(parts) > 2 else ""
        ch.circuit_component = parts[3] if len(parts) > 3 else ""

        if len(parts) > 4:
            try:
                ch.normal_state = int(parts[4])
            except ValueError:
                ch.normal_state = 0

        return ch

    def parse_dat_ascii(self, dat_path: str) -> list:
        """
        Parsea un archivo .dat en formato ASCII.

        Returns:
            Lista de tuplas (sample_num, timestamp, [valores_analogicos],
                             [valores_digitales])
        """
        if not os.path.exists(dat_path):
            raise FileNotFoundError(f"Archivo .dat no encontrado: {dat_path}")

        data = []
        with open(dat_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    continue
                try:
                    sample_num = int(parts[0])
                    timestamp = int(parts[1])
                except ValueError:
                    continue

                num_a = self._config.num_analog if self._config else 0
                num_d = self._config.num_digital if self._config else 0

                analog_vals = []
                for i in range(2, 2 + num_a):
                    if i < len(parts):
                        try:
                            analog_vals.append(float(parts[i]))
                        except ValueError:
                            analog_vals.append(0.0)
                    else:
                        analog_vals.append(0.0)

                digital_vals = []
                for i in range(2 + num_a, 2 + num_a + num_d):
                    if i < len(parts):
                        try:
                            digital_vals.append(int(parts[i]))
                        except ValueError:
                            digital_vals.append(0)
                    else:
                        digital_vals.append(0)

                data.append((sample_num, timestamp, analog_vals, digital_vals))

        return data

    @staticmethod
    def find_cfg_dat_pair(file_path: str) -> Tuple[str, str]:
        """
        Dado un .cfg o .dat, encuentra su complemento.

        Returns:
            Tupla (cfg_path, dat_path)
        """
        base, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()

        if ext_lower == '.cfg':
            cfg_path = file_path
            dat_path = base + '.dat'
            if not os.path.exists(dat_path):
                dat_path = base + '.DAT'
        elif ext_lower == '.dat':
            dat_path = file_path
            cfg_path = base + '.cfg'
            if not os.path.exists(cfg_path):
                cfg_path = base + '.CFG'
        else:
            raise ValueError(f"Extensión no soportada: {ext}")

        return cfg_path, dat_path


class ComtradeStandardTemplate:
    """
    Plantilla del estándar COMTRADE con parámetros editables.
    Sirve como referencia para la validación.
    """

    # Campos estándar con sus descripciones
    STANDARD_FIELDS = {
        # Información general
        'station_name': {
            'category': 'General',
            'description': 'Nombre de la subestación',
            'type': 'str',
            'required': True,
            'example': 'SUBESTACION_115kV'
        },
        'rec_dev_id': {
            'category': 'General',
            'description': 'ID del dispositivo de registro',
            'type': 'str',
            'required': True,
            'example': 'REL_001'
        },
        'rev_year': {
            'category': 'General',
            'description': 'Año de revisión del estándar',
            'type': 'int',
            'required': True,
            'example': '2013',
            'options': ['1991', '1999', '2013']
        },
        'line_freq': {
            'category': 'General',
            'description': 'Frecuencia de la línea (Hz)',
            'type': 'float',
            'required': True,
            'example': '60.0',
            'options': ['50.0', '60.0']
        },
        'data_format': {
            'category': 'General',
            'description': 'Formato de datos',
            'type': 'str',
            'required': True,
            'example': 'ASCII',
            'options': ['ASCII', 'BINARY', 'BINARY32', 'FLOAT32']
        },
    }

    # Señales analógicas estándar típicas para relés de protección
    STANDARD_ANALOG_SIGNALS = [
        {'name': 'IA', 'phase': 'A', 'unit': 'A',
         'desc': 'Corriente fase A'},
        {'name': 'IB', 'phase': 'B', 'unit': 'A',
         'desc': 'Corriente fase B'},
        {'name': 'IC', 'phase': 'C', 'unit': 'A',
         'desc': 'Corriente fase C'},
        {'name': 'IN', 'phase': 'N', 'unit': 'A',
         'desc': 'Corriente de neutro'},
        {'name': 'I0', 'phase': '', 'unit': 'A',
         'desc': 'Corriente secuencia cero'},
        {'name': 'I1', 'phase': '', 'unit': 'A',
         'desc': 'Corriente secuencia positiva'},
        {'name': 'I2', 'phase': '', 'unit': 'A',
         'desc': 'Corriente secuencia negativa'},
        {'name': 'VA', 'phase': 'A', 'unit': 'kV',
         'desc': 'Tensión fase A'},
        {'name': 'VB', 'phase': 'B', 'unit': 'kV',
         'desc': 'Tensión fase B'},
        {'name': 'VC', 'phase': 'C', 'unit': 'kV',
         'desc': 'Tensión fase C'},
        {'name': 'VN', 'phase': 'N', 'unit': 'kV',
         'desc': 'Tensión de neutro'},
        {'name': 'V0', 'phase': '', 'unit': 'kV',
         'desc': 'Tensión secuencia cero'},
        {'name': 'V1', 'phase': '', 'unit': 'kV',
         'desc': 'Tensión secuencia positiva'},
        {'name': 'V2', 'phase': '', 'unit': 'kV',
         'desc': 'Tensión secuencia negativa'},
        {'name': 'P', 'phase': '', 'unit': 'MW',
         'desc': 'Potencia activa'},
        {'name': 'Q', 'phase': '', 'unit': 'MVAR',
         'desc': 'Potencia reactiva'},
        {'name': 'F', 'phase': '', 'unit': 'Hz',
         'desc': 'Frecuencia'},
    ]

    # Señales digitales estándar típicas
    STANDARD_DIGITAL_SIGNALS = [
        {'name': 'TRIP', 'desc': 'Señal de disparo general'},
        {'name': 'TRIP_A', 'desc': 'Disparo fase A'},
        {'name': 'TRIP_B', 'desc': 'Disparo fase B'},
        {'name': 'TRIP_C', 'desc': 'Disparo fase C'},
        {'name': 'CLOSE', 'desc': 'Señal de cierre'},
        {'name': 'RECLOSE', 'desc': 'Recierre automático'},
        {'name': '21_PICKUP', 'desc': 'Arranque protección distancia'},
        {'name': '21_Z1', 'desc': 'Zona 1 distancia'},
        {'name': '21_Z2', 'desc': 'Zona 2 distancia'},
        {'name': '21_Z3', 'desc': 'Zona 3 distancia'},
        {'name': '50_PICKUP', 'desc': 'Arranque instantáneo'},
        {'name': '51_PICKUP', 'desc': 'Arranque temporizado'},
        {'name': '67_FWD', 'desc': 'Direccional adelante'},
        {'name': '67_REV', 'desc': 'Direccional reversa'},
        {'name': '59_PICKUP', 'desc': 'Arranque sobretensión'},
        {'name': '27_PICKUP', 'desc': 'Arranque subtensión'},
        {'name': '81_PICKUP', 'desc': 'Arranque frecuencia'},
        {'name': '87_OPERATE', 'desc': 'Operación diferencial'},
        {'name': 'CB_OPEN', 'desc': 'Interruptor abierto'},
        {'name': 'CB_CLOSE', 'desc': 'Interruptor cerrado'},
        {'name': 'ALARM', 'desc': 'Alarma general'},
        {'name': 'COMM_FAIL', 'desc': 'Falla de comunicación'},
    ]

    @classmethod
    def get_all_standard_signal_names(cls) -> list:
        """Retorna todos los nombres de señales estándar."""
        names = []
        names.extend([s['name'] for s in cls.STANDARD_ANALOG_SIGNALS])
        names.extend([s['name'] for s in cls.STANDARD_DIGITAL_SIGNALS])
        return names

    @classmethod
    def get_standard_by_category(cls) -> dict:
        """Agrupa señales estándar por categoría."""
        result = {
            'Analógicas - Corrientes': [],
            'Analógicas - Tensiones': [],
            'Analógicas - Potencia/Frecuencia': [],
            'Digitales - Protección': [],
            'Digitales - Control': [],
            'Digitales - Supervisión': [],
        }
        for sig in cls.STANDARD_ANALOG_SIGNALS:
            if 'I' in sig['name'][:1]:
                result['Analógicas - Corrientes'].append(sig)
            elif 'V' in sig['name'][:1]:
                result['Analógicas - Tensiones'].append(sig)
            else:
                result['Analógicas - Potencia/Frecuencia'].append(sig)

        for sig in cls.STANDARD_DIGITAL_SIGNALS:
            name = sig['name'].upper()
            if any(k in name for k in ['TRIP', 'PICKUP', 'OPERATE',
                                        'FWD', 'REV', 'Z1', 'Z2', 'Z3']):
                result['Digitales - Protección'].append(sig)
            elif any(k in name for k in ['CLOSE', 'OPEN', 'RECLOSE',
                                          'CB_']):
                result['Digitales - Control'].append(sig)
            else:
                result['Digitales - Supervisión'].append(sig)

        return result
