"""
Modelos de datos para señales de relés de protección.
Compatibles con IEEE C37.111 (COMTRADE) y OMICRON XRIO.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SignalType(Enum):
    ANALOG = "analog"
    BINARY = "binary"


class ProtectionFunction(Enum):
    DISTANCE = "Protección de distancia"
    OVERCURRENT = "Sobrecorriente"
    DIFFERENTIAL = "Diferencial"
    OVERVOLTAGE = "Sobretensión"
    UNDERVOLTAGE = "Subtensión"
    FREQUENCY = "Frecuencia"
    DIRECTIONAL = "Direccional"
    BREAKER_FAILURE = "Falla de interruptor"
    RECLOSING = "Recierre"
    SYNCHROCHECK = "Verificación de sincronismo"
    OVERLOAD = "Sobrecarga"
    GENERAL = "General"
    METERING = "Medición"
    COMMUNICATION = "Comunicación"
    UNKNOWN = "Desconocido"

    @classmethod
    def all_names(cls):
        return [f.value for f in cls]


@dataclass
class AnalogSignal:
    """Señal analógica según COMTRADE / XRIO."""
    index: int = 0
    name: str = ""
    phase: str = ""          # A, B, C, N
    component: str = ""      # V (voltage), I (current)
    unit: str = ""           # kV, A, etc.
    multiplier: float = 1.0
    offset: float = 0.0
    skew: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    primary: float = 1.0
    secondary: float = 1.0
    scaling_ids: str = "P"   # Primary ('P') or Secondary ('S') scaling
    description: str = ""
    status: str = "On"       # XRIO Parameter Status (On/Off)
    secondary: float = 1.0
    ps_type: str = "P"       # P=Primary, S=Secondary
    xrio_block: str = ""     # Bloque AxRADR de origen
    function: ProtectionFunction = ProtectionFunction.UNKNOWN
    standard_name: str = ""  # Nombre estándar mapeado
    description: str = ""    # Descripción larga (UserText/LongName)

    def display_name(self) -> str:
        if self.phase and self.component:
            return f"{self.component}{self.phase}"
        return self.name


@dataclass
class DisturbanceReportSignal:
    """Configuración de señal en reporte de disturbios (B1RBDR)."""
    channel: int
    name: str = ""          # NAMEx
    description: str = ""   # Description of NAMEx
    trig_operation: str = "" # TrigDRx
    trig_level: str = ""    # TrigLevelx
    indication_mask: str = "" # IndicationMax
    set_led: str = ""       # SetLEDx
    block: str = ""         # Bloque origen (e.g. B1RBDR)


@dataclass
class BinarySignal:
    """Señal binaria según COMTRADE / XRIO."""
    index: int = 0
    name: str = ""
    state: int = 0           # 0 o 1
    xrio_block: str = ""     # Bloque BxRBDR de origen
    function: ProtectionFunction = ProtectionFunction.UNKNOWN
    standard_name: str = ""
    description: str = ""    # Descripción larga

    def display_name(self) -> str:
        return self.name


@dataclass
class RelayReference:
    """Referencia/configuración del relé detectada del XRIO."""
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    serial: str = ""
    station_name: str = ""
    device_id: str = ""
    description: str = ""

    def full_id(self) -> str:
        parts = [p for p in [self.manufacturer, self.model, self.firmware] if p]
        return " - ".join(parts) if parts else "Relé desconocido"


@dataclass
class XRIOData:
    """Datos completos extraídos de un archivo XRIO."""
    relay: RelayReference = field(default_factory=RelayReference)
    analog_signals: list = field(default_factory=list)    # list[AnalogSignal]
    binary_signals: list = field(default_factory=list)    # list[BinarySignal]
    disturbance_report_signals: list = field(default_factory=list) # list[DisturbanceReportSignal]
    raw_xml_blocks: dict = field(default_factory=dict)    # nombre_bloque -> xml_string
    file_path: str = ""

    @property
    def total_signals(self) -> int:
        return len(self.analog_signals) + len(self.binary_signals)


@dataclass
class ComtradeChannel:
    """Canal individual de un archivo COMTRADE (.cfg)."""
    index: int = 0
    name: str = ""
    phase: str = ""
    circuit_component: str = ""
    unit: str = ""
    multiplier: float = 1.0
    offset: float = 0.0
    skew: float = 0.0
    min_val: float = -99999.0
    max_val: float = 99999.0
    primary: float = 1.0
    secondary: float = 1.0
    ps_type: str = "P"
    signal_type: SignalType = SignalType.ANALOG
    normal_state: int = 0  # Solo para binarias


@dataclass
class ComtradeConfig:
    """Configuración completa de un par COMTRADE .cfg/.dat."""
    station_name: str = ""
    rec_dev_id: str = ""
    rev_year: int = 1999
    num_analog: int = 0
    num_digital: int = 0
    analog_channels: list = field(default_factory=list)   # list[ComtradeChannel]
    digital_channels: list = field(default_factory=list)   # list[ComtradeChannel]
    line_freq: float = 60.0
    sampling_rates: list = field(default_factory=list)
    start_timestamp: str = ""
    trigger_timestamp: str = ""
    data_format: str = "ASCII"
    time_multiplier: float = 1.0
    file_path: str = ""

    @property
    def total_channels(self) -> int:
        return self.num_analog + self.num_digital


@dataclass
class AliasEntry:
    """Entrada del diccionario de alias."""
    relay_name: str = ""        # Nombre técnico del relé
    standard_name: str = ""     # Nombre estándar COMTRADE
    relay_model: str = ""       # Modelo del relé (para filtrado)
    signal_type: str = "analog" # analog o binary
    function: str = ""          # Función de protección
    auto_detected: bool = False # Si fue detectado automáticamente
    validated: bool = False     # Si fue validado manualmente

    def key(self) -> str:
        return f"{self.relay_model}::{self.relay_name}"


@dataclass
class ValidationResult:
    """Resultado de una validación señal XRIO vs estándar COMTRADE."""
    xrio_name: str = ""
    standard_name: str = ""
    match_type: str = ""       # exact, alias, fuzzy, new, mismatch
    confidence: float = 0.0
    message: str = ""
    alias_entry: Optional[AliasEntry] = None
