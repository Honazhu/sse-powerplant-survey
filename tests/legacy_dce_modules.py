"""Load pure DCE modules without importing oTree models or opening a database."""
import importlib
from pathlib import Path
import sys
import types

package = types.ModuleType('_legacy_dce')
package.__path__ = [str(Path(__file__).resolve().parents[1] / 'random_matrix' / 'legacy_v23')]
sys.modules.setdefault('_legacy_dce', package)
matrix = importlib.import_module('_legacy_dce.matrix')
randomization = importlib.import_module('_legacy_dce.randomization')
exports = importlib.import_module('_legacy_dce.exports')

facility_design = importlib.import_module('_legacy_dce.facility_design')
