# Deployment package for Scaleway Serverless Function
sheetkeeper-deploy.zip: *.py requirements.txt
	mkdir -p package
	pip install -r requirements.txt --target ./package
	rm -f $@
	zip -r $@ *.py package
	ls -l $@

clean:
	rm -rf package
