from nandi import LOAD, NO_LOAD

def __list_all_setup():
    from os.path import dirname, basename, isfile
    import glob

    # This generates a list of modules in this folder for the * in __main__ to work.
    setup_paths = glob.glob(dirname(__file__) + "/*.py")
    all_setup = [basename(f)[:-3] for f in setup_paths if isfile(f)
                   and f.endswith(".py")
                   and not f.endswith('__init__.py')]

    if LOAD or NO_LOAD:
        to_load = LOAD
        if to_load:
            if not all(any(mod == setup_name for setup_name in all_setup) for mod in to_load):
                #LOGGER.error("Invalid loadorder names. Quitting.")
                quit(1)

        else:
            to_load = all_setup

        if NO_LOAD:
            #LOGGER.info("Not loading: {}".format(NO_LOAD))
            return [item for item in to_load if item not in NO_LOAD]

        return to_load

    return all_setup


ALL_SETUP = sorted(__list_all_setup())
#LOGGER.info("Modules to load: %s", str(ALL_SETUP))
__all__ = ALL_SETUP + ["ALL_SETUP"]
