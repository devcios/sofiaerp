FROM odoo:15.0

LABEL MAINTAINER CiosDev <lpalacioslapa@gmail.com>
USER root

RUN pip3 install dropbox

USER odoo
