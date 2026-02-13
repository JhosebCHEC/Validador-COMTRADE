"""
Parser para archivos OMICRON XRIO (XML).
Extrae configuración del relé, señales analógicas (AxRADR) y binarias (BxRBDR).
"""
import os
import re
from lxml import etree
from typing import Optional
from models.signal_models import (
    XRIOData, RelayReference, AnalogSignal, BinarySignal,
    ProtectionFunction, SignalType, DisturbanceReportSignal
)


# Mapa heurístico para clasificar funciones de protección por nombre de señal
FUNCTION_KEYWORDS = {
    ProtectionFunction.DISTANCE: [
        "Z", "DIST", "21", "ZONE", "MHO", "QUAD", "REACH", "IMPEDANCE"
    ],
    ProtectionFunction.OVERCURRENT: [
        "OC", "50", "51", "OVERCURRENT", "I>", "I>>", "IINST", "TOC",
        "DTOC", "IDMT"
    ],
    ProtectionFunction.DIFFERENTIAL: [
        "DIFF", "87", "RESTRAIN", "OPERATE", "BIAS"
    ],
    ProtectionFunction.OVERVOLTAGE: [
        "OV", "59", "V>", "V>>", "OVERVOLT"
    ],
    ProtectionFunction.UNDERVOLTAGE: [
        "UV", "27", "V<", "V<<", "UNDERVOLT"
    ],
    ProtectionFunction.FREQUENCY: [
        "FREQ", "81", "F<", "F>", "ROCOF", "DF/DT"
    ],
    ProtectionFunction.DIRECTIONAL: [
        "DIR", "67", "DIRECTIONAL", "ANGLE", "TORQUE"
    ],
    ProtectionFunction.BREAKER_FAILURE: [
        "BF", "50BF", "BREAKER", "CBF", "CB FAIL"
    ],
    ProtectionFunction.RECLOSING: [
        "RECL", "79", "AUTORECL", "AR", "RECLOSE"
    ],
    ProtectionFunction.SYNCHROCHECK: [
        "SYNC", "25", "SYNCHRO", "CHECK SYNC"
    ],
    ProtectionFunction.METERING: [
        "METER", "MEAS", "MEASURE", "MW", "MVAR", "PF", "KWH"
    ],
    ProtectionFunction.COMMUNICATION: [
        "COMM", "GOOSE", "SV", "IEC61850", "DNP", "MODBUS", "TRIP SEND"
    ],
}


def classify_signal_function(name: str) -> ProtectionFunction:
    """Clasifica una señal por su nombre usando búsqueda heurística."""
    upper = name.upper().replace("_", " ").replace("-", " ")
    for func, keywords in FUNCTION_KEYWORDS.items():
        for kw in keywords:
            if kw in upper:
                return func
    # Clasificar por componente eléctrica básica
    if any(c in upper for c in ["IA", "IB", "IC", "IN", "I0", "I1", "I2"]):
        return ProtectionFunction.OVERCURRENT
    if any(c in upper for c in ["VA", "VB", "VC", "VN", "V0", "V1", "V2",
                                  "UA", "UB", "UC"]):
        return ProtectionFunction.OVERVOLTAGE
    return ProtectionFunction.UNKNOWN


class XRIOParser:
    """Parser para archivos OMICRON XRIO (formato XML)."""

    # Namespaces comunes en archivos XRIO
    NAMESPACES = {
        'xrio': 'http://www.omicron.at/XRIO',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }

    def __init__(self):
        self._tree: Optional[etree._ElementTree] = None
        self._root: Optional[etree._Element] = None
        self._ns: dict = {}

    def parse(self, file_path: str) -> XRIOData:
        """
        Parsea un archivo XRIO y retorna los datos extraídos.
        
        Args:
            file_path: Ruta al archivo .xrio
            
        Returns:
            XRIOData con toda la información extraída
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo XRIO no encontrado: {file_path}")

        data = XRIOData(file_path=file_path)

        try:
            self._tree = etree.parse(file_path)
            self._root = self._tree.getroot()
            self._ns = self._detect_namespaces()

            data.relay = self._extract_relay_reference()
            data.analog_signals = self._extract_analog_signals()
            data.binary_signals = self._extract_binary_signals()
            data.disturbance_report_signals = self._extract_disturbance_report_signals()
            data.raw_xml_blocks = self._extract_raw_blocks()

        except etree.XMLSyntaxError as e:
            raise ValueError(f"Error de sintaxis XML en XRIO: {e}")

        return data

    def _detect_namespaces(self) -> dict:
        """Detecta los namespaces del documento XML."""
        ns = {}
        if self._root is not None:
            ns = dict(self._root.nsmap)
            if None in ns:
                ns['default'] = ns.pop(None)
        return ns

    def _find_elements(self, xpath: str) -> list:
        """Busca elementos usando xpath, con y sin namespace."""
        results = []
        if self._root is None:
            return None

        # Intento directo
        results = self._root.findall(xpath)
        if results:
            return results

        # Intento con namespace por defecto
        if 'default' in self._ns:
            ns_xpath = self._add_default_ns(xpath)
            try:
                results = self._root.findall(ns_xpath, {'ns': self._ns['default']})
            except Exception:
                pass

        # Intento con búsqueda profunda
        if not results:
            tag = xpath.split('/')[-1].split('[')[0]
            results = list(self._root.iter())
            results = [e for e in results if self._clean_tag(e.tag) == tag]

        return results

    def _clean_tag(self, tag) -> str:
        """Remueve namespace del tag."""
        if not isinstance(tag, str):
            return ""
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def _add_default_ns(self, xpath: str) -> str:
        """Agrega namespace por defecto a un xpath."""
        parts = xpath.split('/')
        return '/'.join(f'ns:{p}' if p and not p.startswith('@')
                        and not p.startswith('*') else p for p in parts)

    def _get_text(self, element, child_tag: str, default: str = "") -> str:
        """Obtiene texto de un elemento hijo."""
        if element is None:
            return default
        # Búsqueda directa
        child = element.find(child_tag)
        if child is None:
            # Búsqueda sin namespace
            for ch in element:
                if self._clean_tag(ch.tag) == child_tag:
                    child = ch
                    break
        if child is not None and child.text:
            return child.text.strip()
        return default

    def _get_attr(self, element, attr: str, default: str = "") -> str:
        """Obtiene atributo de un elemento."""
        if element is None:
            return default
        return element.get(attr, default)

    def _resolve_parameter_value(self, param) -> str:
        """Resuelve valor de <Parameter>, usando EnumList cuando aplique (ID_0 -> Off)."""
        if param is None:
            return ""

        raw_val = self._get_text(param, 'Value')
        if not raw_val:
            return ""

        enum_list = None
        for child in param:
            if self._clean_tag(child.tag) == 'EnumList':
                enum_list = child
                break

        if enum_list is not None:
            for enum_val in enum_list:
                if self._clean_tag(enum_val.tag) != 'EnumValue':
                    continue
                if enum_val.get('EnumId') == raw_val and enum_val.text:
                    return enum_val.text.strip()

        return raw_val

    def _extract_relay_reference(self) -> RelayReference:
        """Extrae la referencia/identificación del relé."""
        relay = RelayReference()

        all_elements = list(self._root.iter()) if self._root is not None else []
        tag_map = {}
        for el in all_elements:
            clean = self._clean_tag(el.tag).lower()
            if clean not in tag_map:
                tag_map[clean] = el

        # Buscar ForeignId que contiene el modelo del relé
        # Formato: "IedIdentifier | REC670 | ROS1E1L21R"
        for el in all_elements[:100]:  # Buscar en los primeros 100 elementos
            if self._clean_tag(el.tag).lower() == 'foreignid':
                text = el.text.strip() if el.text else ""
                if "IedIdentifier" in text or "IEDIDENTIFIER" in text.upper():
                    parts = [p.strip() for p in text.split('|')]
                    if len(parts) >= 2:
                        relay.model = parts[1]  # REC670, RED670, etc.
                    if len(parts) >= 3:
                        relay.firmware = parts[2]
                    break

        # Buscar información del relé en diferentes ubicaciones posibles
        relay_tags = {
            'manufacturer': ['manufacturer', 'vendor', 'make'],
            'serial': ['serial', 'serialnumber', 'serial_number'],
            'station_name': ['stationname', 'station', 'substation',
                             'station_name'],
            'device_id': ['deviceid', 'device_id', 'devid', 'ieddesc',
                          'iedname', 'name'],
            'description': ['description', 'desc', 'comment'],
        }

        for field_name, tags in relay_tags.items():
            for tag in tags:
                if tag in tag_map:
                    el = tag_map[tag]
                    text = el.text.strip() if el.text else ""
                    if not text:
                        text = el.get('value', el.get('Value', ''))
                    if text:
                        setattr(relay, field_name, text)
                        break

        # Si no encontramos modelo en ForeignId, buscar en atributos del root
        if not relay.model and self._root is not None:
            for attr in self._root.attrib:
                if 'type' in attr.lower() or 'model' in attr.lower():
                    relay.model = self._root.get(attr, '')
                    break

        # Buscar en elementos de configuración genéricos
        for el in all_elements:
            clean = self._clean_tag(el.tag).lower()
            if 'config' in clean or 'setting' in clean or 'header' in clean:
                for child in el:
                    ctag = self._clean_tag(child.tag).lower()
                    text = child.text.strip() if child.text else ""
                    if not text:
                        continue
                    if not relay.manufacturer and any(
                            k in ctag for k in ['manuf', 'vendor', 'make']):
                        relay.manufacturer = text
                    if not relay.model and any(
                            k in ctag for k in ['model', 'type', 'device']):
                        relay.model = text

        # Establecer fabricante por defecto si tenemos modelo ABB
        if not relay.manufacturer and relay.model:
            if any(m in relay.model.upper() for m in ['REC', 'RED', 'REB', 'REL', 'REG']):
                relay.manufacturer = "ABB"

        return relay

    def _is_metadata(self, name: str) -> bool:
        """Determina si un nombre corresponde a metadata/configuración y no a una señal real."""
        if not name:
            return True
            
        upper = name.upper().replace("_", " ").strip()
        
        # Lista negra de palabras/frases que indican configuración
        BAD_SUBSTRINGS = [
            "MANUFACTURER", "STATION", "DEVICE", "PROTECTED OBJECT",
            "RESIDUAL FACTOR", "SAMPLE RATE", "SAMPLERATE", "FREQUENCY", 
            "DATE", "TIME", "VERSION", "REVISION", "RECORDER", "TRIGGER", 
            "HEADER", "SETTING", "LENGTH", "DURATION", "PREFAULT", "POSTFAULT",
            "HARDWARE", "LINE FREQ", "IED NAME", "SHORT NAME", "LONG NAME"
        ]
        
        # Coincidencia exacta con lista negra expandida
        BAD_EXACT = [
            "ID", "NAME", "UNIT", "PHASE", "TYPE", "SERIAL", "MODEL", 
            "LOCATION", "USER", "DESCRIPTION", "COMMENT"
        ]
        
        if upper in BAD_EXACT:
            return True
            
        for bad in BAD_SUBSTRINGS:
            if bad in upper:
                return True
                
        return False

    def _extract_analog_signals(self) -> list:
        """Extrae señales analógicas de bloques AxRADR."""
        signals = []
        if self._root is None:
            return signals

        all_elements = list(self._root.iter())
        idx = 1

        # Buscar bloques AxRADR (Analog x Relay Analog Data Record)
        for el in all_elements:
            tag = self._clean_tag(el.tag)

            # --- ESTRATEGIA ABB PCM600 (Block + Parameter) ---
            if tag == 'Block':
                b_name_text = self._get_text(el, 'Name')
                # Ej: "A1RADR: 1" -> busca A1RADR
                match_abb = re.search(r'(A\d*RADR)', b_name_text, re.IGNORECASE)
                if match_abb:
                    block_name = match_abb.group(1).upper()
                    
                    # Buscar bloque "General" adentro, o usar el mismo bloque
                    target_block = el
                    for child in el:
                        if self._clean_tag(child.tag) == 'Block':
                            c_name = self._get_text(child, 'Name')
                            if c_name and c_name.upper() == 'GENERAL':
                                target_block = child
                                break
                    
                    # Recolectar parámetros por índice (NAME1, Operation01, NomValue01, etc)
                    # Mapa: index_str -> {attr: value}
                    data_map = {}
                    
                    for param in target_block.iter():
                        if self._clean_tag(param.tag) == 'Parameter':
                            p_name = self._get_text(param, 'Name') # Ej: NAME1
                            p_val = self._resolve_parameter_value(param)
                            
                            # Extraer sufijo numérico
                            # Casos: NAME1, Operation01, NomValue01
                            # Regex busca digitos al final
                            m_idx = re.search(r'(\d+)$', p_name)
                            if m_idx:
                                idx_str = m_idx.group(1)
                                idx_int = int(idx_str)
                                prefix = p_name[:-len(idx_str)].upper()
                                
                                if idx_int not in data_map:
                                    data_map[idx_int] = {'index': idx_int}
                                
                                # Mapear atributos
                                if prefix == 'NAME':
                                    data_map[idx_int]['name'] = p_val
                                elif prefix == 'NOMVALUE':
                                    data_map[idx_int]['primary'] = p_val
                                elif prefix == 'OPERATION': # Estado (On/Off) - Podemos guardarlo
                                    data_map[idx_int]['status'] = p_val
                                elif prefix == 'UNIT': 
                                    pass 
                                
                                # Intentar leer Unidad del hijo <Unit>
                                u_el = param.find('Unit')
                                if u_el is not None and u_el.text:
                                    data_map[idx_int]['unit'] = u_el.text.strip()

                    # Crear señales
                    for i in sorted(data_map.keys()):
                        d = data_map[i]
                        if 'name' not in d or not d['name']:
                            continue
                            
                        sig = AnalogSignal(index=d['index'], xrio_block=block_name)
                        sig.name = d['name']
                        if 'primary' in d:
                            try:
                                sig.primary = float(d['primary'])
                            except:
                                pass
                        if 'unit' in d:
                            sig.unit = d['unit']
                        if 'status' in d:
                            sig.status = d['status']
                        
                        # Auto-detectar fase/componente
                        self._autofill_analog_attributes(sig)
                        
                        signals.append(sig)
                        idx += 1
                        
                    continue # Siguiente elemento del loop principal

            # Patroness: A1RADR, A2RADR, etc. o AxRADR
            if re.match(r'^A\d*RADR$', tag, re.IGNORECASE):
                block_name = tag
                
                # Estrategia 1: Buscar elementos específicos 'Channel' o 'Signal'
                found_specific = False
                for child in el.iter():
                    ctag = self._clean_tag(child.tag).lower()
                    if ctag in ['channel', 'signal', 'analogchannel', 'analogsignal']:
                        sig = self._parse_analog_element(child, idx, block_name)
                        if sig and sig.name and not self._is_metadata(sig.name):
                            signals.append(sig)
                            idx += 1
                        found_specific = True
                
                if found_specific:
                    continue

                # Estrategia 2: Iteración general pero MÁS ESTRICTA
                for child in el.iter():
                    ctag = self._clean_tag(child.tag)
                    lower_tag = ctag.lower()
                    
                    # Filtro de tags válidos para señales
                    if any(k in lower_tag for k in
                           ['input', 'output', 'ainput', 'aoutput', 'analog']):
                        sig = self._parse_analog_element(child, idx, block_name)
                        if sig and sig.name and not self._is_metadata(sig.name):
                             signals.append(sig)
                             idx += 1

                # Estrategia 3: Fallback (hijos directos)
                if not any(s.xrio_block == block_name for s in signals):
                    for child in el:
                        ctag = self._clean_tag(child.tag)
                        if any(x in ctag.lower() for x in ['setting', 'param', 'header', 'info', 'config']):
                            continue
                            
                        # Si tiene atributos numéricos como multiplier/primary, es probable candidata
                        if (child.get('primary') or child.get('Primary') or 
                            child.get('multiplier') or child.get('Multiplier')):
                             sig = self._parse_analog_from_generic(child, idx, block_name)
                             if sig and sig.name and not self._is_metadata(sig.name):
                                signals.append(sig)
                                idx += 1

        # Si no bloques AxRADR, intentar fallback
        if not signals:
            signals = self._fallback_extract_analog(all_elements)

        return signals

    def _autofill_analog_attributes(self, sig: AnalogSignal):
        """Auto-detecta fase y componente basados en el nombre y unidad de la señal."""
        # Auto-detectar fase del nombre
        if not sig.phase and sig.name:
            upper = sig.name.upper()
            if upper.endswith('A') or '_A' in upper or 'PH_A' in upper:
                sig.phase = 'A'
            elif upper.endswith('B') or '_B' in upper or 'PH_B' in upper:
                sig.phase = 'B'
            elif upper.endswith('C') or '_C' in upper or 'PH_C' in upper:
                sig.phase = 'C'
            elif 'N' in upper[-2:] or 'NEUTRAL' in upper:
                sig.phase = 'N'

        # Auto-detectar componente (V/I)
        if sig.name:
            upper = sig.name.upper()
            if any(k in upper for k in ['VOLT', 'V_', '_V', 'UA', 'UB', 'UC']):
                sig.component = 'V'
            elif any(k in upper for k in ['CURR', 'I_', '_I', 'AMP']):
                sig.component = 'I'
            elif sig.unit:
                if 'V' in sig.unit.upper() or 'VOLT' in sig.unit.upper():
                    sig.component = 'V'
                elif 'A' in sig.unit.upper() or 'AMP' in sig.unit.upper():
                    sig.component = 'I'
        
        # Clasificar función si no está asignada o refinarla
        if not sig.function or sig.function == ProtectionFunction.UNKNOWN:
             sig.function = classify_signal_function(sig.name)

    def _parse_analog_element(self, el, idx: int,
                               block: str) -> Optional[AnalogSignal]:
        """Parsea un elemento que representa una señal analógica."""
        sig = AnalogSignal(index=idx, xrio_block=block)

        # Intento de nombre corto (ej: VA)
        sig.name = (el.get('ShortName', '') or el.get('shortName', '')
                    or el.get('name', '') or el.get('Name', '')
                    or el.get('id', '') or self._get_text(el, 'ShortName')
                    or self._get_text(el, 'Name')
                    or self._get_text(el, 'name')
                    or self._clean_tag(el.tag))

        # Descripción / UserText
        sig.description = (el.get('UserText', '') or el.get('Description', '')
                           or el.get('LongName', '') or self._get_text(el, 'UserText')
                           or self._get_text(el, 'Description')
                           or self._get_text(el, 'LongName')
                           or "")
                           
        # Si description está vacía y name parece descriptivo, podríamos usar name
        # Pero mejor dejarlo así.
        
        sig.unit = (el.get('unit', '') or el.get('Unit', '')
                    or self._get_text(el, 'Unit')
                    or self._get_text(el, 'unit'))

        sig.phase = (el.get('phase', '') or el.get('Phase', '')
                     or self._get_text(el, 'Phase'))

        # Auto-detectar fase del nombre
        if not sig.phase and sig.name:
            upper = sig.name.upper()
            if upper.endswith('A') or '_A' in upper or 'PH_A' in upper:
                sig.phase = 'A'
            elif upper.endswith('B') or '_B' in upper or 'PH_B' in upper:
                sig.phase = 'B'
            elif upper.endswith('C') or '_C' in upper or 'PH_C' in upper:
                sig.phase = 'C'
            elif 'N' in upper[-2:] or 'NEUTRAL' in upper:
                sig.phase = 'N'

        # Auto-detectar componente (V/I)
        if sig.name:
            upper = sig.name.upper()
            if any(k in upper for k in ['VOLT', 'V_', '_V', 'UA', 'UB', 'UC']):
                sig.component = 'V'
            elif any(k in upper for k in ['CURR', 'I_', '_I', 'AMP']):
                sig.component = 'I'
            elif sig.unit:
                if 'V' in sig.unit.upper() or 'VOLT' in sig.unit.upper():
                    sig.component = 'V'
                elif 'A' in sig.unit.upper() or 'AMP' in sig.unit.upper():
                    sig.component = 'I'

        # Valores numéricos
        for attr in ['multiplier', 'offset', 'min_value', 'max_value',
                      'primary', 'secondary']:
            val_str = (el.get(attr, '') or el.get(attr.capitalize(), '')
                       or self._get_text(el, attr)
                       or self._get_text(el, attr.capitalize()))
            if val_str:
                try:
                    setattr(sig, attr, float(val_str))
                except ValueError:
                    pass

        sig.function = classify_signal_function(sig.name)
        return sig

    def _parse_analog_from_generic(self, el, idx: int,
                                    block: str) -> Optional[AnalogSignal]:
        """Parsea señal analógica de un elemento genérico."""
        sig = AnalogSignal(index=idx, xrio_block=block)
        name = (el.get('name', '') or el.get('Name', '') or el.get('id', '')
                or (el.text.strip() if el.text else ''))
        if not name:
            name = self._clean_tag(el.tag)
        sig.name = name
        sig.function = classify_signal_function(name)

        # Extraer atributos adicionales
        for attr_name in el.attrib:
            val = el.get(attr_name)
            lower = attr_name.lower()
            if 'unit' in lower:
                sig.unit = val
            elif 'phase' in lower:
                sig.phase = val
            elif 'primary' in lower:
                try:
                    sig.primary = float(val)
                except ValueError:
                    pass
            elif 'secondary' in lower:
                try:
                    sig.secondary = float(val)
                except ValueError:
                    pass

        return sig

    def _fallback_extract_analog(self, all_elements: list) -> list:
        """Extrae señales analógicas cuando no hay bloques AxRADR."""
        # signals = []
        # idx = 1
        # 
        # for el in all_elements:
        #     tag = self._clean_tag(el.tag).lower()
        #     if any(k in tag for k in ['analoginput', 'analogchannel',
        #                                'ainput', 'ct', 'vt', 'current',
        #                                'voltage']):
        #         sig = self._parse_analog_element(el, idx, "FALLBACK")
        #         if sig and sig.name:
        #             signals.append(sig)
        #             idx += 1
        # return signals
        return []

    def _extract_binary_signals(self) -> list:
        """Extrae señales binarias de bloques BxRBDR."""
        signals = []
        if self._root is None:
            return signals

        all_elements = list(self._root.iter())
        idx = 1
        
        # Buscar bloques BxRBDR (Binary x Relay Binary Data Record)
        for el in all_elements:
            tag = self._clean_tag(el.tag)
            if re.match(r'^B\d*RBDR$', tag, re.IGNORECASE):
                block_name = tag
                
                # Estrategia 1: Tags específicos
                found = False
                for child in el.iter():
                    ctag = self._clean_tag(child.tag).lower()
                    if ctag in ['channel', 'signal', 'binarychannel', 'binarysignal', 'status', 'digital']:
                        sig = self._parse_binary_element(child, idx, block_name)
                        if sig and sig.name and not self._is_metadata(sig.name):
                            signals.append(sig)
                            idx += 1
                        found = True
                        
                if found:
                    continue

                # Estrategia 2: Iteración más amplia pero sin 'param'
                for child in el.iter():
                    ctag = self._clean_tag(child.tag)
                    if any(k in ctag.lower() for k in
                           ['input', 'output', 'binary', 'digital']):
                        sig = self._parse_binary_element(
                            child, idx, block_name)
                        if sig and sig.name and not self._is_metadata(sig.name):
                            signals.append(sig)
                            idx += 1

                # Fallback: hijos directos excluyendo params
                if not any(s.xrio_block == block_name for s in signals):
                    for child in el:
                        ctag = self._clean_tag(child.tag).lower()
                        if any(x in ctag for x in ['setting', 'param', 'header']):
                            continue
                        sig = self._parse_binary_from_generic(
                            child, idx, block_name)
                        if sig and sig.name and not self._is_metadata(sig.name):
                            signals.append(sig)
                            idx += 1

        # Fallback global
        # if not signals:
        #    signals = self._fallback_extract_binary(all_elements)

        return signals

    def _parse_binary_element(self, el, idx: int,
                               block: str) -> Optional[BinarySignal]:
        """Parsea un elemento de señal binaria."""
        sig = BinarySignal(index=idx, xrio_block=block)
        
        sig.name = (el.get('ShortName', '') or el.get('shortName', '')
                    or el.get('name', '') or el.get('Name', '')
                    or el.get('id', '') or self._get_text(el, 'ShortName') 
                    or self._get_text(el, 'Name')
                    or self._get_text(el, 'name')
                    or self._clean_tag(el.tag))
                    
        sig.description = (el.get('UserText', '') or el.get('Description', '')
                           or el.get('LongName', '') or self._get_text(el, 'UserText')
                           or self._get_text(el, 'Description')
                           or self._get_text(el, 'LongName')
                           or "")

        state_str = (el.get('state', '') or el.get('normalState', '')
                     or el.get('NormalState', ''))
        if state_str:
            try:
                sig.state = int(state_str)
            except ValueError:
                sig.state = 0

        sig.function = classify_signal_function(sig.name)
        return sig

    def _parse_binary_from_generic(self, el, idx: int,
                                    block: str) -> Optional[BinarySignal]:
        """Parsea señal binaria de un elemento genérico."""
        sig = BinarySignal(index=idx, xrio_block=block)
        name = (el.get('name', '') or el.get('Name', '') or el.get('id', '')
                or (el.text.strip() if el.text else ''))
        if not name:
            name = self._clean_tag(el.tag)
        sig.name = name
        sig.function = classify_signal_function(name)
        return sig

    def _fallback_extract_binary(self, all_elements: list) -> list:
        """Extrae señales binarias cuando no hay bloques BxRBDR."""
        signals = []
        idx = 1
        for el in all_elements:
            tag = self._clean_tag(el.tag).lower()
            if any(k in tag for k in ['binaryinput', 'binaryoutput',
                                       'digitalinput', 'digitaloutput',
                                       'binput', 'boutput', 'status',
                                       'trip', 'close', 'alarm']):
                sig = self._parse_binary_element(el, idx, "FALLBACK")
                if sig and sig.name:
                    signals.append(sig)
                    idx += 1
        return signals

    def _extract_disturbance_report_signals(self) -> list:
        """
        Extrae la configuración del reporte de disturbios (e.g. B1RBDR, B2RBDR).
        Busca bloques BxRBDR -> ID_GENERAL y parsea los parámetros.
        """
        signals: list[DisturbanceReportSignal] = []
        if self._root is None:
            return signals

        # 1. Encontrar todos los bloques "ID_GENERAL" cuyo padre sea BxRBDR
        target_blocks = [] # Lista de tuplas (bloque_general, nombre_bloque_padre)
        
        for elem in self._root.iter():
            tag = self._clean_tag(elem.tag)
            if tag == 'Block' and elem.get('Id') == 'ID_GENERAL':
                parent = elem.getparent()
                if parent is not None:
                    # Chequeamos nombre o ID del padre para ver si es BxRBDR
                    p_id = parent.get('Id', '')
                    p_name = self._get_text(parent, 'Name')
                    
                    found_block_name = None
                    
                    # Pattern B\d*RBDR (case insensitive)
                    # Chequear en ID primero (ej: ID_B1RBDR1 -> B1RBDR)
                    if p_id:
                        match_id = re.search(r'(B\d*RBDR)', p_id, re.IGNORECASE)
                        if match_id:
                            found_block_name = match_id.group(1)
                    
                    # Chequear en Name si no encontrado
                    if not found_block_name and p_name:
                         match_name = re.search(r'(B\d*RBDR)', p_name, re.IGNORECASE)
                         if match_name:
                             found_block_name = match_name.group(1)

                    if found_block_name:
                         target_blocks.append((elem, found_block_name))

        if not target_blocks:
            return signals

        # 2. Procesar cada bloque encontrado
        for target_block, block_name in target_blocks:
            # Parsear parámetros del bloque
            params_map = {}
            for param in target_block:
                if self._clean_tag(param.tag) != 'Parameter':
                    continue
                
                p_name_tag = self._get_text(param, 'Name')
                if not p_name_tag: 
                    continue

                p_desc = self._get_text(param, 'Description')
                p_val_raw = self._get_text(param, 'Value')

                # Resolver Enum
                final_val = p_val_raw
                enum_list = None
                for child in param:
                    if self._clean_tag(child.tag) == 'EnumList':
                        enum_list = child
                        break
                if enum_list is not None:
                    for enum_val in enum_list:
                        if self._clean_tag(enum_val.tag) == 'EnumValue':
                            if enum_val.get('EnumId') == p_val_raw:
                                if enum_val.text:
                                    final_val = enum_val.text
                                break
                
                params_map[p_name_tag] = {'val': final_val, 'desc': p_desc}


            # 3. Iterar canales 1..96 para ESTE bloque
            for i in range(1, 97):
                suffix_idx = str(i)
                suffix_pad = f"{i:02d}"
                
                name_key = f"NAME{suffix_idx}"
                if name_key not in params_map:
                    name_key = f"NAME{suffix_pad}"
                
                if name_key not in params_map:
                    continue

                name_data = params_map[name_key]
                
                trig_op = params_map.get(f"TrigDR{suffix_pad}", {'val': '', 'desc': ''})
                if not trig_op['val'] and f"TrigDR{suffix_idx}" in params_map:
                    trig_op = params_map[f"TrigDR{suffix_idx}"]

                trig_lev = params_map.get(f"TrigLevel{suffix_pad}", {'val': '', 'desc': ''})
                if not trig_lev['val'] and f"TrigLevel{suffix_idx}" in params_map:
                    trig_lev = params_map[f"TrigLevel{suffix_idx}"]

                ind_mask = params_map.get(f"IndicationMa{suffix_pad}", {'val': '', 'desc': ''})
                if not ind_mask['val'] and f"IndicationMa{suffix_idx}" in params_map:
                    ind_mask = params_map[f"IndicationMa{suffix_idx}"]

                set_led = params_map.get(f"SetLED{suffix_pad}", {'val': '', 'desc': ''})
                if not set_led['val'] and f"SetLED{suffix_idx}" in params_map:
                    set_led = params_map[f"SetLED{suffix_idx}"]
                
                sig = DisturbanceReportSignal(
                    channel=i,
                    name=name_data['val'],
                    description=name_data['desc'], 
                    trig_operation=trig_op['val'],
                    trig_level=trig_lev['val'],
                    indication_mask=ind_mask['val'],
                    set_led=set_led['val'],
                    block=block_name
                )
                signals.append(sig)

        return signals

    def _extract_raw_blocks(self) -> dict:
        """Extrae los bloques XML crudos para visualización."""
        blocks = {}
        if self._root is None:
            return blocks

        for el in self._root.iter():
            tag = self._clean_tag(el.tag)
            if (re.match(r'^[AB]\d*R[AB]DR$', tag, re.IGNORECASE)
                    or 'config' in tag.lower()
                    or 'header' in tag.lower()):
                try:
                    blocks[tag] = etree.tostring(
                        el, pretty_print=True, encoding='unicode')
                except Exception:
                    blocks[tag] = f"<{tag}>...</{tag}>"

        return blocks

    def get_block_names(self) -> list:
        """Retorna nombres de todos los bloques encontrados."""
        if self._root is None:
            return []
        names = []
        for el in self._root.iter():
            tag = self._clean_tag(el.tag)
            if re.match(r'^[AB]\d*R[AB]DR$', tag, re.IGNORECASE):
                if tag not in names:
                    names.append(tag)
        return names
