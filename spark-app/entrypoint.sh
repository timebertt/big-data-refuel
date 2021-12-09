#!/usr/bin/env bash

set -x
set -o errexit
set -o pipefail

master="${MASTER:-local}"

deploy_mode=
if [ -n "${DEPLOY_MODE}" ] ; then
  deploy_mode="$(printf -- '--deploy-mode %s' ${DEPLOY_MODE})"
fi

driver_host=
if [ -n "${POD_IP}" ] ; then
  driver_host="--conf spark.driver.host=${POD_IP}"
fi

spark-submit --verbose \
	--master "$master" $deploy_mode $driver_host \
	--conf "spark.jars.ivy=${IVY_PACKAGE_DIR}" \
	--packages "${SPARK_KAFKA_DEPENDENCY}" \
	--packages "${SPARK_MYSQL_DEPENDENCY}" \
	--py-files /app/dependencies.zip \
	"$@"
