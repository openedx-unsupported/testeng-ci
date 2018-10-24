import click


@click.command()
@click.option(
    '--log-file',
    help="File name of console log .txt file from a Jenkins build "
    "that ran pytest-xdist.",
    required=True
)
@click.option(
    '--worker',
    help="Pytest worker that ran the test list. Example: gw0",
    required=True
)
@click.option(
    '--test-suite',
    help="Test suite that the pytest worker ran. Example: lms-unit",
    required=True
)
def main(log_file, worker, test_suite):
    """
    Strips the console log of a pytest-xdist Jenkins run into the test list
    of an individual worker.

    Assumes a format of:
    [test-suite] [worker] RESULT test
    """
    test_string_prefix = "[{}] [{}]".format(test_suite, worker)
    test_list_file = '{}_{}_test_list.txt'.format(test_suite, worker)
    outputFileOpened = False
    with open(log_file, 'r') as console_file:
        for line in console_file:
            if test_string_prefix in line:
                if not outputFileOpened:
                    output_file = open(test_list_file, 'w')
                    outputFileOpened = True
                output_file.write(line.split()[3]+'\n')

    if outputFileOpened:
        output_file.close()
    else:
        raise StandardError("No tests found for test-suite: {} and worker: {}".format(test_suite, worker))


if __name__ == "__main__":
    main()
