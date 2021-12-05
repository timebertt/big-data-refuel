#!/usr/bin/env bash

set -x
set -o errexit
set -o pipefail

master="${MASTER:-local}"

deploy_mode=
if [ -n "${DEPLOY_MODE}" ] ; then
  deploy_mode="$(printf -- '--deploy-mode %s' ${DEPLOY_MODE})"
fi

spark-submit --verbose \
	--master "$master" $deploy_mode \
	--conf "spark.jars.ivy=${IVY_PACKAGE_DIR}" \
	--conf "spark.driver.host=${POD_IP}" \
	--packages "${SPARK_KAFKA_DEPENDENCY}" \
	--packages "${SPARK_MYSQL_DEPENDENCY}" \
	--py-files /app/dependencies.zip \
	"$@"
