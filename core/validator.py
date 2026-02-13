"""
Motor de validación inteligente.
Compara señales XRIO con el estándar COMTRADE y gestiona el diccionario de alias.
"""
import re
from typing import Optional
from models.signal_models import (
    XRIOData, ComtradeConfig, AnalogSignal, BinarySignal,
    AliasEntry, ValidationResult, ProtectionFunction
)
from core.alias_database import AliasDatabase
from core.comtrade_parser import ComtradeStandardTemplate


class SignalValidator:
    """Validador inteligente de señales XRIO contra estándar COMTRADE."""

    def __init__(self, alias_db: AliasDatabase):
        self._alias_db = alias_db
        self._standard_names = (
            ComtradeStandardTemplate.get_all_standard_signal_names()
        )

    def validate(self, xrio_data: XRIOData,
                 comtrade_config: Optional[ComtradeConfig] = None) -> list:
        """
        Valida las señales del XRIO contra el estándar COMTRADE.

        Args:
            xrio_data: Datos parseados del XRIO
            comtrade_config: Configuración COMTRADE opcional para
                             comparación directa

        Returns:
            Lista de ValidationResult
        """
        results = []
        relay_model = xrio_data.relay.model or "UNKNOWN"

        # Validar señales analógicas
        for sig in xrio_data.analog_signals:
            result = self._validate_signal(
                sig.name, relay_model, 'analog', comtrade_config)
            results.append(result)

        # Validar señales binarias
        for sig in xrio_data.binary_signals:
            result = self._validate_signal(
                sig.name, relay_model, 'binary', comtrade_config)
            results.append(result)

        return results

    def _validate_signal(self, xrio_name: str, relay_model: str,
                          signal_type: str,
                          comtrade_config: Optional[ComtradeConfig]
                          ) -> ValidationResult:
        """Valida una señal individual."""
        result = ValidationResult(xrio_name=xrio_name)

        # 1. Búsqueda exacta en el estándar
        if xrio_name.upper() in [n.upper() for n in self._standard_names]:
            result.standard_name = xrio_name
            result.match_type = 'exact'
            result.confidence = 1.0
            result.message = 'Coincidencia exacta con estándar'
            self._auto_add_alias(
                xrio_name, xrio_name, relay_model, signal_type, True)
            return result

        # 2. Búsqueda en el diccionario de alias
        alias_name = self._alias_db.find_standard_for(relay_model, xrio_name)
        if alias_name:
            result.standard_name = alias_name
            result.match_type = 'alias'
            result.confidence = 0.95
            result.message = f'Mapeado por alias: {xrio_name} → {alias_name}'
            return result

        # 3. Comparación con COMTRADE cargado
        if comtrade_config:
            channels = (comtrade_config.analog_channels
                        if signal_type == 'analog'
                        else comtrade_config.digital_channels)
            for ch in channels:
                if self._fuzzy_match(xrio_name, ch.name):
                    result.standard_name = ch.name
                    result.match_type = 'fuzzy'
                    result.confidence = 0.7
                    result.message = (
                        f'Coincidencia aproximada con COMTRADE: {ch.name}')
                    self._auto_add_alias(
                        xrio_name, ch.name, relay_model, signal_type, True)
                    return result

        # 4. Búsqueda heurística
        best_match = self._heuristic_match(xrio_name, signal_type)
        if best_match:
            result.standard_name = best_match
            result.match_type = 'fuzzy'
            result.confidence = 0.5
            result.message = (
                f'Posible coincidencia heurística: {best_match}')
            return result

        # 5. Sin coincidencia - señalar como nueva
        result.match_type = 'new'
        result.confidence = 0.0
        result.message = 'Sin coincidencia. Requiere mapeo manual.'
        return result

    def _fuzzy_match(self, name1: str, name2: str) -> bool:
        """Verifica si dos nombres de señal son similares."""
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        if n1 == n2:
            return True

        # Verificar si uno contiene al otro
        if n1 in n2 or n2 in n1:
            return True

        # Verificar componentes clave (fase + tipo)
        phase1 = self._extract_phase(n1)
        phase2 = self._extract_phase(n2)
        type1 = self._extract_signal_type_indicator(n1)
        type2 = self._extract_signal_type_indicator(n2)

        if phase1 and phase2 and type1 and type2:
            return phase1 == phase2 and type1 == type2

        return False

    def _normalize_name(self, name: str) -> str:
        """Normaliza un nombre de señal para comparación."""
        n = name.upper().strip()
        n = re.sub(r'[_\-\s\.]+', '', n)
        # Remover prefijos comunes de fabricantes
        prefixes = ['REL_', 'DIG_', 'ANA_', 'BIN_', 'CH_', 'SIG_']
        for prefix in prefixes:
            if n.startswith(prefix.replace('_', '')):
                n = n[len(prefix) - 1:]
        return n

    def _extract_phase(self, name: str) -> str:
        """Extrae la fase de un nombre de señal."""
        n = name.upper()
        if n.endswith('A') or 'PHA' in n or '_A' in n:
            return 'A'
        if n.endswith('B') or 'PHB' in n or '_B' in n:
            return 'B'
        if n.endswith('C') or 'PHC' in n or '_C' in n:
            return 'C'
        if 'N' in n[-2:] or 'NEUT' in n:
            return 'N'
        return ''

    def _extract_signal_type_indicator(self, name: str) -> str:
        """Extrae el indicador de tipo (V o I) de un nombre."""
        n = name.upper()
        if any(k in n for k in ['VOLT', 'V_', '_V', 'VA', 'VB', 'VC',
                                  'UA', 'UB', 'UC', 'TENSION']):
            return 'V'
        if any(k in n for k in ['CURR', 'I_', '_I', 'IA', 'IB', 'IC',
                                  'AMP', 'CORR']):
            return 'I'
        return ''

    def _heuristic_match(self, xrio_name: str, signal_type: str
                          ) -> Optional[str]:
        """Intenta encontrar un nombre estándar usando heurísticas."""
        n = self._normalize_name(xrio_name)
        phase = self._extract_phase(n)
        sig_ind = self._extract_signal_type_indicator(n)

        if signal_type == 'analog':
            candidates = ComtradeStandardTemplate.STANDARD_ANALOG_SIGNALS
        else:
            candidates = ComtradeStandardTemplate.STANDARD_DIGITAL_SIGNALS

        for std in candidates:
            std_norm = self._normalize_name(std['name'])
            if std_norm in n or n in std_norm:
                return std['name']
            # Coincidir por fase + tipo
            if signal_type == 'analog' and phase and sig_ind:
                std_name = std['name']
                if (sig_ind in std_name.upper()
                        and phase in std_name.upper()):
                    return std_name

        return None

    def _auto_add_alias(self, relay_name: str, standard_name: str,
                        relay_model: str, signal_type: str,
                        auto: bool = True):
        """Agrega automáticamente un alias al diccionario."""
        from core.xrio_parser import classify_signal_function
        func = classify_signal_function(relay_name)

        entry = AliasEntry(
            relay_name=relay_name,
            standard_name=standard_name,
            relay_model=relay_model,
            signal_type=signal_type,
            function=func.value,
            auto_detected=auto,
            validated=not auto,
        )
        self._alias_db.add(entry)

    def auto_validate_and_update(self, xrio_data: XRIOData,
                                  comtrade_config: Optional[
                                      ComtradeConfig] = None
                                  ) -> dict:
        """
        Ejecuta validación completa y retorna un resumen.

        Returns:
            dict con conteos: exact, alias, fuzzy, new, total
        """
        results = self.validate(xrio_data, comtrade_config)

        summary = {
            'exact': 0, 'alias': 0, 'fuzzy': 0, 'new': 0, 'total': 0,
            'results': results
        }

        for r in results:
            summary['total'] += 1
            if r.match_type in summary:
                summary[r.match_type] += 1

        return summary
