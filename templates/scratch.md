SOC:
=== Customer Pain ===
Customer replicated Beanstalk environment within same VPC. First Environment can connect to Redis Server, Second Environment Cannot
=== Customer Questions ===
Why can I connect to Redis via first environment, but not the second.
=== Previous actions ===
01/24 09:10(UTC) granbroo: 
Checked both environments are in same VPC
Checked that Redis Server will allow traffic from different subnets.
Confirmed Redis is healthy
Check ENV1 works.
Check ENV2 doesn't work.
Checked IAM for permissions.
Noted broken ENV2 instance had 100%CPU spike and went unhealthy for a short time
Received full logs from customer - nginx log shows errors connecting to 127.0.0.1:8042 (connection refused) and redis has the getaddrinfo ENOTFOUND error
Confirmed no user initiated IPTables running, and nginx.confs across both instances are identical. Second instance seems to have far fewer listening applications.
Confirmed client cloned environment using AWS Console Tool
01/25 07:48(UTC) gargana: 

=== Next steps ===

=== Customer resources ===
EC 
https://elmo-op-use1.amazon.com/rds-op-service/web/search?q=alive5-stage
Env 1
https://k2.amazon.com/workbench/scripts/aws/Chronos-beanstalk/index.html?accountID=864798833616&region=us-east-1&appname=alive5-api&envname=alive5-api-stage
Env 2
https://k2.amazon.com/workbench/scripts/aws/Chronos-beanstalk/index.html?accountID=864798833616&region=us-east-1&appname=alive5-api&envname=alive5-api-v2-stage
Redis
https://k2.amazon.com/workbench/scripts/aws/ElastiCache_DescribeCluster?accountIds=864798833616&Region=us-east-1&_run=1
VPC for SG for Redis (sg-68f2d117)
https://admiral-iad.ec2.amazon.com/vpc/864798833616/vpc-98878bfe

### JQ FUN

aws ec2 describe-instances  --filters Name=image-id,Values=ami-fc8a1985 \ 
  | jq '.[][] \ 
  | .Instances[] \
  | {InsanceId:.InstanceId,PrivateDns:.PrivateDnsName,PublicDns:.PublicDnsName,State:.State.Name} \
  | select(.State|contains("running"))'
