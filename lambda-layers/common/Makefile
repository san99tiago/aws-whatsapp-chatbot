install:
	[ -d "modules/python" ] || python3 -m pip install -r requirements.txt -t modules/python/ --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all:

clean:
	rm -rf modules/python
