try:
    import importlib.metadata
    __version__ = importlib.metadata.version(__package__ or __name__)
except importlib.metadata.PackageNotFoundError:
    # Fallback version when not installed as a package
    __version__ = "1.0.0"
