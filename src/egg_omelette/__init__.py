import os
import sys
import shutil
import logging
import importlib.metadata

from pkg_resources import get_distribution

NAMESPACE_STANZA = """# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
"""

logger = logging.getLogger()


symlink = os.symlink
islink = os.path.islink
rmtree = shutil.rmtree
unlink = None

def makedirs(target, is_namespace=False):
    """ Similar to os.makedirs, but adds __init__.py files as it goes.  Returns a boolean
        indicating success.
    """
    drive, path = os.path.splitdrive(target)
    parts = path.split(os.path.sep)
    current = drive + os.path.sep
    for part in parts:
        current = os.path.join(current, part)
        if islink(current):
            return False
        if not os.path.exists(current):
            os.mkdir(current)
            init_filename = os.path.join(current, "__init__.py")
            if not os.path.exists(init_filename):
                init_file = open(init_filename, "w")
                if is_namespace or part == "Products":
                    init_file.write(NAMESPACE_STANZA)
                else:
                    init_file.write("# mushroom")
                init_file.close()
    return True

WIN32 = False


def main():
    """Main entry point for the egg-omelette console script."""
    location = os.getcwd()
    
        for package in importlib.metadata.distributions():
            project_name = package.name
            namespaces = {}
            dist = get_distribution(package.name)
            for line in dist._get_metadata("namespace_packages.txt"):
                ns = namespaces
                for part in line.split("."):
                    ns = ns.setdefault(part, {})
            top_level = sorted(list(dist._get_metadata("top_level.txt")))

            def create_namespaces(namespaces, ns_base=()):
                for k, v in namespaces.items():
                    ns_parts = ns_base + (k,)
                    link_dir = os.path.join(location, *ns_parts)
                    if not os.path.exists(link_dir):
                        if not makedirs(link_dir, is_namespace=True):
                            logger.warn(
                                "Warning: (While processing egg %s) Could not create namespace directory (%s).  Skipping."
                                % (project_name, link_dir)
                            )
                            continue
                    if len(v) > 0:
                        create_namespaces(v, ns_parts)
                    egg_ns_dir = os.path.join(dist.location, *ns_parts)
                    if not os.path.isdir(egg_ns_dir):
                        logger.info(
                            "(While processing egg %s) Package '%s' is zipped.  Skipping."
                            % (project_name, os.path.sep.join(ns_parts))
                        )
                        continue
                    dirs = os.listdir(egg_ns_dir)
                    for name in dirs:
                        if name.startswith("."):
                            continue
                        name_parts = ns_parts + (name,)
                        src = os.path.join(dist.location, *name_parts)
                        dst = os.path.join(location, *name_parts)
                        if os.path.exists(dst):
                            continue
                        symlink(src, dst)
            create_namespaces(namespaces)
            for package_name in top_level:
                if package_name in namespaces:
                    # These are processed in create_namespaces
                    continue
                else:
                    if not os.path.isdir(dist.location):
                        logger.info(
                            "(While processing egg %s) Package '%s' is zipped.  Skipping."
                            % (project_name, package_name)
                        )
                        continue

                    package_location = os.path.join(dist.location, package_name)
                    link_location = os.path.join(location, package_name)
                    # check for single python module
                    if not os.path.exists(package_location):
                        package_location = os.path.join(
                            dist.location, package_name + ".py"
                        )
                        link_location = os.path.join(
                            location, package_name + ".py"
                        )
                    # check for native libs
                    # XXX - this should use native_libs from above
                    if not os.path.exists(package_location):
                        package_location = os.path.join(
                            dist.location, package_name + ".so"
                        )
                        link_location = os.path.join(
                            location, package_name + ".so"
                        )
                    if not os.path.exists(package_location):
                        package_location = os.path.join(
                            dist.location, package_name + ".dll"
                        )
                        link_location = os.path.join(
                            location, package_name + ".dll"
                        )
                    if not os.path.exists(package_location):
                        logger.warn(
                            "Warning: (While processing egg %s) Package '%s' not found.  Skipping."
                            % (project_name, package_name)
                        )
                        continue
                if not os.path.exists(link_location):
                    if WIN32 and not os.path.isdir(package_location):
                        logger.warn(
                            "Warning: (While processing egg %s) Can't link files on Windows (%s -> %s).  Skipping."
                            % (project_name, package_location, link_location)
                        )
                        continue
                    try:
                        symlink(package_location, link_location)
                    except OSError as e:
                        logger.warn(
                            "While processing egg %s) symlink fails (%s, %s). Skipping.\nOriginal Exception:\n%s"
                            % (
                                project_name,
                                package_location,
                                link_location,
                                str(e),
                            )
                        )
                    # except:
                    #    # TODO: clearify if recipe should fail on error or resume by skipping.
                    #    # Possible solution, add a recipe option, stop_on_fail that will quit buildout on general exceptions
                    #    self.logger.warn("Unexpected error :\nWhile processing egg %s) symlink fails (%s, %s). Skipping.\nOriginal Exception:\n%s" % (project_name, package_location, link_location, sys.exc_info()[0]))
                else:
                    logger.info(
                        "(While processing egg %s) Link already exists (%s -> %s).  Skipping."
                        % (project_name, package_location, link_location)
                    )
                    continue


if __name__ == "__main__":
    main()
