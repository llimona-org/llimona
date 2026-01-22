def init():
    from .addons import Addons

    Addons().register_all_providers()
