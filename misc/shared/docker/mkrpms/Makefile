all: centos-mkrpms

centos-mkrpms: centos-epel
	echo "Building centos-mkrpms"
	docker build --tag openbxi/centos-mkrpms \
		     --rm=true \
		     --file Dockerfile.centos-mkrpms \
		     --build-arg HTTP_PROXY=$(http_proxy)\
		     --build-arg HTTPS_PROXY=${https_proxy}\
		     --build-arg FTP_PROXY=${ftp_proxy}\
		     --build-arg NO_PROXY=${no_proxy}\
		     --build-arg http_proxy=$(http_proxy)\
		     --build-arg https_proxy=${https_proxy}\
		     --build-arg ftp_proxy=${ftp_proxy}\
		     --build-arg no_proxy=${no_proxy}\
		     ${PWD}


centos-epel:
	echo "Building centos-epel"
	docker build --tag openbxi/centos-epel \
		     --rm=true \
		     --file Dockerfile.centos-epel \
		     --build-arg HTTP_PROXY=$(http_proxy)\
		     --build-arg HTTPS_PROXY=${https_proxy}\
		     --build-arg FTP_PROXY=${ftp_proxy}\
		     --build-arg NO_PROXY=${no_proxy}\
		     --build-arg http_proxy=$(http_proxy)\
		     --build-arg https_proxy=${https_proxy}\
		     --build-arg ftp_proxy=${ftp_proxy}\
		     --build-arg no_proxy=${no_proxy}\
		     ${PWD}
