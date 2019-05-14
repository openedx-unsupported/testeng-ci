upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade:
	pip install -qr requirements/pip-tools.txt
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/testing.txt requirements/testing.in
	pip-compile --upgrade -o requirements/travis.txt requirements/travis.in
	pip-compile --upgrade -o requirements/aws.txt requirements/aws.in

