install:
	[ -d "modules/python" ] || pip install -r requirements.txt -t modules/python/ --platform manylinux2014_x86_64 --only-binary=:all:

clean:
	rm -rf modules/python
