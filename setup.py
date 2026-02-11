"""
Setup script for q21-referee package with Cython compilation.

This builds the internal modules (_*.py) as compiled extensions,
while keeping the public API (callbacks.py, runner.py, types.py, errors.py)
as readable Python source.
"""

from setuptools import setup, find_packages, Extension
import os
import sys

# Check if Cython is available
try:
    from Cython.Build import cythonize
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False
    print("Cython not found. Building without compilation (source only).")

# Internal modules to compile with Cython
CYTHON_MODULES = [
    "src/q21_referee/_message_router.py",
    "src/q21_referee/_callback_executor.py",
    "src/q21_referee/_validator.py",
    "src/q21_referee/_context_builder.py",
    "src/q21_referee/_envelope_builder.py",
    "src/q21_referee/_state.py",
    "src/q21_referee/_email_client.py",
    "src/q21_referee/_logging_config.py",
]


def get_extensions():
    """Build Extension objects for Cython compilation."""
    if not USE_CYTHON:
        return []

    extensions = []
    for module_path in CYTHON_MODULES:
        if os.path.exists(module_path):
            # Convert path to module name: src/q21_referee/_foo.py -> q21_referee._foo
            module_name = module_path.replace("src/", "").replace("/", ".").replace(".py", "")
            extensions.append(
                Extension(
                    name=module_name,
                    sources=[module_path],
                )
            )
    return extensions


def get_ext_modules():
    """Get extension modules, cythonized if Cython is available."""
    extensions = get_extensions()
    if not extensions:
        return []

    return cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
        # Don't fail if some files are missing (for development)
        nthreads=os.cpu_count() or 1,
    )


# Only add ext_modules if we have Cython
ext_modules = get_ext_modules() if USE_CYTHON else []

setup(
    name="q21-referee",
    version="1.0.0",
    description="Q21 Referee SDK - Implement AI callbacks for the Q21 League game",
    author="Course Staff",
    license="Proprietary",
    python_requires=">=3.10",
    packages=find_packages(where="src") + ["sdk", "sdk.llm_sdk", "sdk.protocol_sdk"],
    package_dir={"": "src", "sdk": "sdk", "sdk.llm_sdk": "sdk/llm_sdk", "sdk.protocol_sdk": "sdk/protocol_sdk"},
    ext_modules=ext_modules,
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "llm": ["anthropic>=0.18.0"],
        "gmail": [
            "google-api-python-client>=2.100.0",
            "google-auth>=2.23.0",
            "google-auth-oauthlib>=1.1.0",
            "google-auth-httplib2>=0.1.0",
        ],
        "all": [
            "anthropic>=0.18.0",
            "google-api-python-client>=2.100.0",
            "google-auth>=2.23.0",
            "google-auth-oauthlib>=1.1.0",
            "google-auth-httplib2>=0.1.0",
        ],
        "dev": [
            "cython>=3.0",
            "build",
            "wheel",
        ],
    },
    # Include compiled .so/.pyd files in the package
    package_data={
        "q21_referee": ["*.so", "*.pyd"],
    },
    # Exclude source files for internal modules in wheel
    exclude_package_data={
        "q21_referee": ["_*.py"] if USE_CYTHON else [],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Cython",
    ],
)
