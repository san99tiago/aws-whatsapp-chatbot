####################################################################################
# AGENT MAKEFILE: builds the AgentCore Runtime deployment package (direct code ZIP)
# --> Dependencies MUST target Linux arm64 (AgentCore Runtime architecture)
####################################################################################

install:
	[ -d "dist/package" ] || python3 -m pip install -r requirements.txt -t dist/package/ --platform manylinux2014_aarch64 --python-version 3.13 --only-binary=:all: --no-compile
	cp -f main.py dist/package/
	rm -rf dist/package/tools
	cp -R tools dist/package/tools
	find dist/package -type d -name "__pycache__" -prune -exec rm -rf {} +
	find dist/package -name "*.pyc" -delete

clean:
	rm -rf dist
