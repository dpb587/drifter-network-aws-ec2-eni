Tool for managing drifting network interfaces on AWS.


## Vagrant

    AWS_VAGRANT_IAM_PROFILE_NAME=safetest \
    AWS_VAGRANT_SUBNET_ID=subnet-abcd1234 \
    AWS_VAGRANT_SECURITY_GROUPS=sg-abcd1234 \
    vagrant up --provider aws


## Example

**create**

    R0=$( aws --region us-east-1 ec2 create-network-interface --subnet-id "$AWS_VAGRANT_SUBNET_ID" --groups "$AWS_VAGRANT_SECURITY_GROUPS" )
    NETWORK_ID=$( echo "$R0" | jq -r '.NetworkInterface.NetworkInterfaceId' )

**attach**

    vagrant ssh -c "cd /vagrant ; sudo -E ./bin/run.py --env-file /tmp/network.env -vv attach '$NETWORK_ID'"

**usage**

    vagrant ssh -c ". /tmp/network.env ; mkdir -p /tmp/mountme ; sudo mkfs -t ext4 \$MOUNT_DEVICE ; sudo mount \$MOUNT_DEVICE /tmp/mountme ; sudo chown ubuntu:ubuntu /tmp/mountme ; date >> /tmp/mountme/verify.txt ; cat /tmp/mountme/verify.txt ; sudo umount /tmp/mountme"

**detach**

    vagrant ssh -c "cd /vagrant ; sudo -E ./bin/run.py -vv detach '$NETWORK_ID'"

**destroy**

    R1=$( aws --region us-east-1 ec2 delete-network-interface --network-interface-id "$NETWORK_ID" )


## Docker

    sudo docker build -t dpb587/drifter-network-aws-ec2-eni .


## systemd

**service** - `network-enif2881bab-drifter.service`

    [Service]
    RemainAfterExit=yes
    ExecStart=/usr/bin/docker run -v /media/drifter:/docker-mnt dpb587/drifter-network-aws-ec2-eni --env-file /docker-mnt/enif2881bab.network.env attach eni-f2881bab
    ExecStop=/usr/bin/docker run dpb587/drifter-network-aws-ec2-eni detach eni-f2881bab

**service** - `network-enif2881bab-drifter-routes.service`

    [Unit]
    BindsTo=network-enif2881bab-drifter.service

    [Service]
    RemainAfterExit=yes
    EnvironmentFile=/media/drifter/enif2881bab.network.env
    ExecStart=/bin/bash -c "ip route add default via ${NETWORK_GATEWAY} dev ${NETWORK_DEVICE} table 1${NETWORK_DEVICEN} && ip rule add from ${NETWORK_IP0} lookup 1${NETWORK_DEVICEN}"
    ExecStop=/bin/bash -c "ip route del default via ${NETWORK_GATEWAY} dev ${NETWORK_DEVICE} table 1${NETWORK_DEVICEN} ; ip rule del from ${NETWORK_IP0} lookup 1${NETWORK_DEVICEN} ; /bin/true"

    [X-Fleet]
    X-ConditionMachineOf=network-enif2881bab-drifter.service


## Notes

You might need to override routes...

    ip route add default via 192.168.210.1 dev eth1 table 51
    ip rule add from 192.168.210.68 lookup 51


## License

[MIT License](./LICENSE)
