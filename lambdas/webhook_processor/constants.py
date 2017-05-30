EDX_PLATFORM_BASE_TESTS = [
    "-accessibility-",
    "-bok-choy-",
    "-js-",
    "-lettuce-",
    "-python-unittests-",
    "-quality-",
]

EDX_PLATFORM_MASTER = ["edx-platform" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_PR = ["edx-platform" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]

EDX_PLATFORM_EUCALYPTUS_MASTER = ["eucalyptus" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_EUCALYPTUS_PR = ["eucalyptus" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]

EDX_PLATFORM_FICUS_MASTER = ["ficus" + base + "master" for base in EDX_PLATFORM_BASE_TESTS]
EDX_PLATFORM_FICUS_PR = ["ficus" + base + "pr" for base in EDX_PLATFORM_BASE_TESTS]