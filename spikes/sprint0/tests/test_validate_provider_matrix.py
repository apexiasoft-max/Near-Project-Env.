import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_provider_matrix.py"
SPEC = importlib.util.spec_from_file_location("validate_provider_matrix", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class ProviderMatrixTests(unittest.TestCase):
    def setUp(self):
        matrix_path = ROOT / "provider-matrix" / "provider-observations.json"
        self.matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    def test_repository_matrix_is_valid_as_an_in_progress_matrix(self):
        module.validate_matrix(self.matrix)

    def test_repository_matrix_is_complete_for_provider_access_observations(self):
        module.validate_matrix(self.matrix, require_complete=True)

    def test_complete_mode_requires_both_providers(self):
        self.matrix["sites"][0]["observations"] = [
            observation
            for observation in self.matrix["sites"][0]["observations"]
            if observation["provider"] != "google"
        ]
        with self.assertRaisesRegex(module.MatrixValidationError, "Google and Neshan"):
            module.validate_matrix(self.matrix, require_complete=True)

    def test_duplicate_site_id_is_rejected(self):
        self.matrix["sites"][1]["site_id"] = self.matrix["sites"][0]["site_id"]
        with self.assertRaisesRegex(module.MatrixValidationError, "duplicate site_id"):
            module.validate_matrix(self.matrix)

    def test_invalid_coordinate_is_rejected(self):
        self.matrix["sites"][0]["latitude"] = 100
        with self.assertRaisesRegex(module.MatrixValidationError, "invalid latitude"):
            module.validate_matrix(self.matrix)


if __name__ == "__main__":
    unittest.main()
