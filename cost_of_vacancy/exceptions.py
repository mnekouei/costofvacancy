class HospitalNotFoundError(Exception):
    """No CMS Hospital General Information record matched the given name."""


class AmbiguousHospitalError(Exception):
    """Multiple plausible hospitals matched and none was a clear best match."""

    def __init__(self, query, candidates):
        self.query = query
        self.candidates = candidates  # list of (score, facility_name, state) tuples
        names = ", ".join(f"{name} ({state})" for _, name, state in candidates)
        super().__init__(f"'{query}' matched multiple hospitals ambiguously: {names}. Pass --state to narrow it down.")
