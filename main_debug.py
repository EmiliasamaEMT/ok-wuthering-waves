if __name__ == '__main__':
    from src.update_repo import prepare_update_repository

    update_cache_warning = prepare_update_repository(__file__)
    from src.pyappify_compat import install_prerelease_comparison

    version_compare_warning = install_prerelease_comparison()
    from config import config
    from ok import OK

    config = config
    config['debug'] = True
    # config['click_screenshots_folder'] = "click_screenshots"  # debug用 点击后截图文件夹]
    ok = OK(config)
    for logger_name, warning in (('UpdateRepository', update_cache_warning),
                                 ('UpdateCompatibility', version_compare_warning)):
        if warning:
            from ok.util.logger import Logger
            Logger.get_logger(logger_name).warning(warning)
    ok.start()
