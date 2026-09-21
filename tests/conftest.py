"""Make the test runtime classification explicit before application imports."""

import os


os.environ["ENVIRONMENT"] = "test"
