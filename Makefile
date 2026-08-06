####################################################################################
# ROOT MAKEFILE: orchestrates the Lambda Layers and the AgentCore Agent packaging
####################################################################################

install:
	cd lambda-layers && $(MAKE) install
	cd agent && $(MAKE) install

clean:
	cd lambda-layers && $(MAKE) clean
	cd agent && $(MAKE) clean
