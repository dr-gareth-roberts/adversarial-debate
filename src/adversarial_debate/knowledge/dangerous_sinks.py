DANGEROUS_SINKS: dict[str, list[str]] = {
    "python": [
        "eval",
        "exec",
        "compile",
        "os.system",
        "subprocess.Popen(shell=True)",
        "subprocess.run(shell=True)",
        "subprocess.check_output(shell=True)",
        "pickle.loads",
        "yaml.load",
        "marshal.loads",
        "__import__",
        "importlib.import_module",
        "open",
        "pathlib.Path.write_text",
        "requests.get",
        "urllib.request.urlopen",
    ]
}
