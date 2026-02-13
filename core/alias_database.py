"""
Base de datos dinámica de alias.
Mapea nombres técnicos de relé a nombres estándar COMTRADE.
Persistencia en JSON local.
"""
import json
import os
from typing import Optional
from models.signal_models import AliasEntry


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'alias_database.json'
)


class AliasDatabase:
    """Base de datos de alias: nombre técnico de relé <-> nombre estándar."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._entries: dict = {}  # key -> AliasEntry
        self._load()

    # ---------- Persistencia ----------

    def _load(self):
        """Carga la base de datos desde disco."""
        if os.path.exists(self._db_path):
            try:
                with open(self._db_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                for key, data in raw.items():
                    self._entries[key] = AliasEntry(**data)
            except (json.JSONDecodeError, TypeError, KeyError):
                self._entries = {}

    def save(self):
        """Guarda la base de datos a disco."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        raw = {}
        for key, entry in self._entries.items():
            raw[key] = {
                'relay_name': entry.relay_name,
                'standard_name': entry.standard_name,
                'relay_model': entry.relay_model,
                'signal_type': entry.signal_type,
                'function': entry.function,
                'auto_detected': entry.auto_detected,
                'validated': entry.validated,
            }
        with open(self._db_path, 'w', encoding='utf-8') as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)

    # ---------- CRUD ----------

    def add(self, entry: AliasEntry) -> bool:
        """
        Agrega o actualiza una entrada.
        Retorna True si fue nueva, False si se actualizó.
        """
        key = entry.key()
        is_new = key not in self._entries
        self._entries[key] = entry
        self.save()
        return is_new

    def remove(self, relay_model: str, relay_name: str) -> bool:
        """Elimina una entrada. Retorna True si existía."""
        key = f"{relay_model}::{relay_name}"
        if key in self._entries:
            del self._entries[key]
            self.save()
            return True
        return False

    def get(self, relay_model: str, relay_name: str) -> Optional[AliasEntry]:
        """Obtiene una entrada por modelo y nombre técnico."""
        key = f"{relay_model}::{relay_name}"
        return self._entries.get(key)

    def find_by_relay_name(self, relay_name: str) -> list:
        """Busca entradas por nombre técnico (cualquier modelo)."""
        results = []
        for entry in self._entries.values():
            if entry.relay_name.lower() == relay_name.lower():
                results.append(entry)
        return results

    def find_by_standard_name(self, standard_name: str) -> list:
        """Busca entradas por nombre estándar."""
        results = []
        for entry in self._entries.values():
            if entry.standard_name.lower() == standard_name.lower():
                results.append(entry)
        return results

    def find_standard_for(self, relay_model: str,
                          relay_name: str) -> Optional[str]:
        """
        Dado un modelo y nombre de relé, retorna el nombre estándar.
        Primero busca exacto, luego sin modelo.
        """
        entry = self.get(relay_model, relay_name)
        if entry:
            return entry.standard_name

        # Buscar sin modelo específico
        matches = self.find_by_relay_name(relay_name)
        if matches:
            return matches[0].standard_name

        return None

    def search(self, query: str) -> list:
        """Busca entradas por coincidencia parcial en todos los campos."""
        query_lower = query.lower()
        results = []
        for entry in self._entries.values():
            if (query_lower in entry.relay_name.lower()
                    or query_lower in entry.standard_name.lower()
                    or query_lower in entry.relay_model.lower()
                    or query_lower in entry.function.lower()):
                results.append(entry)
        return results

    def get_all(self) -> list:
        """Retorna todas las entradas como lista."""
        return list(self._entries.values())

    def get_by_model(self, relay_model: str) -> list:
        """Retorna todas las entradas para un modelo de relé."""
        return [e for e in self._entries.values()
                if e.relay_model.lower() == relay_model.lower()]

    def get_by_function(self, function: str) -> list:
        """Retorna entradas filtradas por función de protección."""
        return [e for e in self._entries.values()
                if e.function.lower() == function.lower()]

    def get_models(self) -> list:
        """Retorna lista única de modelos de relé en la BD."""
        models = set()
        for entry in self._entries.values():
            if entry.relay_model:
                models.add(entry.relay_model)
        return sorted(models)

    def get_functions(self) -> list:
        """Retorna lista única de funciones en la BD."""
        functions = set()
        for entry in self._entries.values():
            if entry.function:
                functions.add(entry.function)
        return sorted(functions)

    @property
    def count(self) -> int:
        return len(self._entries)

    def clear(self):
        """Limpia toda la base de datos."""
        self._entries.clear()
        self.save()

    def import_from_json(self, file_path: str) -> int:
        """Importa entradas desde un archivo JSON externo. Retorna conteo."""
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        count = 0
        for key, data in raw.items():
            entry = AliasEntry(**data)
            if self.add(entry):
                count += 1
        return count

    def export_to_json(self, file_path: str):
        """Exporta la base de datos a un archivo JSON."""
        raw = {}
        for key, entry in self._entries.items():
            raw[key] = {
                'relay_name': entry.relay_name,
                'standard_name': entry.standard_name,
                'relay_model': entry.relay_model,
                'signal_type': entry.signal_type,
                'function': entry.function,
                'auto_detected': entry.auto_detected,
                'validated': entry.validated,
            }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
