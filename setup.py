from setuptools import setup


setup(
    name="nora-local-ai",
    version="0.1.0",
    description="Nora is a local-first personal AI assistant.",
    packages=["mini_agent", "mini_agent.providers", "mini_agent.toolkits"],
    package_data={"mini_agent": ["static/*.html", "static/*.svg"]},
    include_package_data=True,
    install_requires=["playwright==1.60.0", "prompt_toolkit>=3.0"],
    extras_require={
        "mcp": ["mcp>=1.0"],
    },
    entry_points={
        "console_scripts": [
            "nora=mini_agent.app:main",
            "nora-serve=mini_agent.app:serve",
            "nora-mcp=mini_agent.mcp_server:main",
        ]
    },
)
