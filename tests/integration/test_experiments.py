"""All cases require an exact authorization value; collection is offline."""
import os

import pytest

from lab.experiment_runner import run
from lab.experiments import CASES


@pytest.mark.integration
@pytest.mark.parametrize('case', CASES)
def test_bounded_experiment(case):
    if (os.getenv('DDSLAB_RUN_INTEGRATION') != '1'
            or os.getenv('DDSLAB_APPROVE_SCENARIO') != case):
        pytest.skip('requires explicit per-scenario approval')
    run(case)
