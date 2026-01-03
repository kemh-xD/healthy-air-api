class DomainException(Exception):
    pass

class InvalidMeasurementError(DomainException):
    pass

class DataSourceError(DomainException):
    pass