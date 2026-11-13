if __name__ == '__main__':
    from src.update_repo import prepare_update_repository

    update_cache_warning = prepare_update_repository(__file__)
    from config import config
    from ok import OK

    config = config
    ok = OK(config)
    if update_cache_warning:
        from ok.util.logger import Logger
        Logger.get_logger('UpdateRepository').warning(update_cache_warning)
    ok.start()
