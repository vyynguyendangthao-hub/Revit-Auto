"""Utilities for creating Revit levels from Dynamo Python (Revit 2024+)."""

from Autodesk.Revit.DB import BuiltInParameter, FilteredElementCollector, Level
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager


def _get_base_elevation(base_level):
    """Return elevation in Revit internal units (feet)."""
    if isinstance(base_level, Level):
        return base_level.Elevation

    if isinstance(base_level, (int, float)):
        return float(base_level)

    raise TypeError("base_level must be a Revit Level or a numeric elevation.")


def _build_elevations(base_elevation, number_of_levels, first_height, typical_height):
    """Generate level elevations from user inputs."""
    if number_of_levels <= 0:
        raise ValueError("number_of_levels must be greater than 0.")

    if first_height <= 0:
        raise ValueError("first_height must be greater than 0.")

    if typical_height <= 0:
        raise ValueError("typical_height must be greater than 0.")

    elevations = []
    current = base_elevation + first_height

    for _ in range(number_of_levels):
        elevations.append(current)
        current += typical_height

    return elevations


def _safe_rename_level(level, target_name, existing_names):
    """Rename level while avoiding duplicate names."""
    name = target_name
    counter = 1

    while name in existing_names:
        counter += 1
        name = "{} ({})".format(target_name, counter)

    param = level.get_Parameter(BuiltInParameter.DATUM_TEXT)
    if param and not param.IsReadOnly:
        param.Set(name)
    else:
        level.Name = name

    existing_names.add(name)


def create_levels(base_level, number_of_levels, first_height, typical_height):
    """Create Revit levels above a base level and return created Level elements.

    Args:
        base_level (Level | float): Base Revit level element or base elevation.
        number_of_levels (int): Number of new levels to create.
        first_height (float): Offset from base elevation to first new level.
        typical_height (float): Repeating offset between the remaining levels.

    Returns:
        list[Level]: Newly created Revit Level elements.

    Raises:
        TypeError: If base_level is neither a Level nor a numeric elevation.
        ValueError: If any numeric input is invalid.
        RuntimeError: If level creation fails.
    """
    doc = DocumentManager.Instance.CurrentDBDocument

    try:
        number_of_levels = int(number_of_levels)
        first_height = float(first_height)
        typical_height = float(typical_height)

        base_elevation = _get_base_elevation(base_level)
        elevations = _build_elevations(
            base_elevation, number_of_levels, first_height, typical_height
        )

        existing_names = set(
            level.Name for level in FilteredElementCollector(doc).OfClass(Level)
        )
        created_levels = []

        TransactionManager.Instance.EnsureInTransaction(doc)
        for index, elevation in enumerate(elevations, start=1):
            level = Level.Create(doc, elevation)
            _safe_rename_level(level, "Level {}".format(index), existing_names)
            created_levels.append(level)

        TransactionManager.Instance.TransactionTaskDone()
        return created_levels

    except Exception as exc:
        try:
            TransactionManager.Instance.ForceCloseTransaction()
        except Exception:
            pass
        raise RuntimeError("Failed to create levels: {}".format(exc))
