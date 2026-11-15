"""Load pure DCE modules without importing oTree models or opening a database."""
import importlib
from pathlib import Path
import sys
import types

package = types.ModuleType('_pure_dce')
package.__path__ = [str(Path(__file__).resolve().parents[1] / 'random_matrix')]
sys.modules.setdefault('_pure_dce', package)
matrix = importlib.import_module('_pure_dce.matrix')
randomization = importlib.import_module('_pure_dce.randomization')
exports = importlib.import_module('_pure_dce.exports')

facility_design = importlib.import_module('_pure_dce.facility_design')
