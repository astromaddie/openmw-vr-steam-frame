import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class DiagnosticGuardTests(unittest.TestCase):
    def test_confirmed_idle_override_requires_a_finite_short_deadline(self):
        source = Path(os.environ['OPENMW_SOURCE'])
        program = r'''
#include "components/xr/diagnosticguard.hpp"
#include <cassert>
int main() {
    using XR::boundedConfirmedIdleDiagnostic;
    assert(boundedConfirmedIdleDiagnostic("1", "12"));
    assert(boundedConfirmedIdleDiagnostic("1", "60"));
    assert(!boundedConfirmedIdleDiagnostic(nullptr, "12"));
    assert(!boundedConfirmedIdleDiagnostic("0", "12"));
    assert(!boundedConfirmedIdleDiagnostic("1", nullptr));
    assert(!boundedConfirmedIdleDiagnostic("1", "0"));
    assert(!boundedConfirmedIdleDiagnostic("1", "61"));
    assert(!boundedConfirmedIdleDiagnostic("1", "nan"));
    assert(!boundedConfirmedIdleDiagnostic("1", "inf"));
    assert(!boundedConfirmedIdleDiagnostic("1", "12junk"));
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'guard.cpp').write_text(program)
            subprocess.run(['c++', '-std=c++20', '-I', str(source), str(root / 'guard.cpp'), '-o', str(root / 'guard')], check=True)
            subprocess.run([str(root / 'guard')], check=True)


if __name__ == '__main__':
    unittest.main()
