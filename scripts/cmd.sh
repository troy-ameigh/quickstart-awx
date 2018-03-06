#!/bin/sh

aws cloudformation create-stack \
  --stack-name "AWXTest" \
  --template-body file://./templates/awx-master.template \
  --parameters file://./ci/dev-gargana.json \
  --capabilities "CAPABILITY_IAM" \
  --disable-rollback  

