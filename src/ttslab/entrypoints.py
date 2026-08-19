from __future__ import annotations

from .console import configure_utf8_stdio


def product_main() -> int:
    configure_utf8_stdio()
    from .product_cli import main

    return main()


def lab_main() -> int:
    configure_utf8_stdio()
    from .cli import main

    return main()
