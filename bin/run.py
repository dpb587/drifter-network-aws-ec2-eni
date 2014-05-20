#!/usr/bin/env python

import argparse
import boto.ec2
import boto.vpc
import os
import simplejson
import subprocess
import sys
import time
import urllib2
import ipaddress

cli = argparse.ArgumentParser(description='Utility for attaching or detaching a network interface on AWS.')
cli.add_argument('action', help='Action to perform (i.e. attach, detach)')
cli.add_argument('networkinterfaceid', help='Network Interface ID (e.g. eni-abcd1234)')
cli.add_argument('--wait', help='Wait until interface is connected', action='store_true')
cli.add_argument('--env-file', help='Write mount environment variables file')
cli.add_argument('--env-prefix', help='Prefix for mount environment variables', default='NETWORK_')
cli.add_argument('--verbose', '-v', action='count', help='Use multiple times to increase verbosity: none = quiet, 1 = completions, 2 = summaries, 3 = details')

cliargs = cli.parse_args()


#
# setup our basics
#

devices = {
  1 : 'eth1',
  2 : 'eth2',
  3 : 'eth3',
  4 : 'eth4',
  5 : 'eth5',
  6 : 'eth6',
  7 : 'eth7',
}

devicesAvailable = devices.copy()

DEVNULL = open(os.devnull, 'w')

if cliargs.verbose > 2:
  TASK_STDOUT = None
  TASK_STDERR = None
else:
  TASK_STDOUT = DEVNULL
  TASK_STDERR = DEVNULL

ec2instance = simplejson.loads(urllib2.urlopen('http://169.254.169.254/latest/dynamic/instance-identity/document').read())
ec2api = boto.ec2.connect_to_region(ec2instance['region'])
vpcapi = boto.vpc.connect_to_region(ec2instance['region'])


#
# verify we can/should attach
#

mounted = False

if cliargs.verbose > 1:
  sys.stderr.write('enumerating network interfaces...\n')

networkinterfaces = ec2api.get_all_network_interfaces(filters = {
  'attachment.instance-id' : ec2instance['instanceId'],
})

for networkinterface in networkinterfaces:
  if cliargs.verbose > 2:
    sys.stderr.write(' + %s -> %s\n' % ( networkinterface.attachment.device_index, networkinterface.id ))

  if cliargs.networkinterfaceid == networkinterface.id:
    mounted = networkinterface

  if networkinterface.attachment.device_index in devicesAvailable:
    del devicesAvailable[networkinterface.attachment.device_index]

if cliargs.verbose > 0:
  sys.stderr.write('enumerated network interfaces\n')


#
# attach if necessary
#

if 'attach' == cliargs.action:
  if False == mounted:
    device = list(devicesAvailable.keys())[0]

    mounted = ec2api.get_all_network_interfaces(filters = {
      'network-interface-id' : cliargs.networkinterfaceid,
    }).pop()

    if cliargs.verbose > 1:
      sys.stderr.write('attaching (%s)...\n' % device)

    ec2api.attach_network_interface(cliargs.networkinterfaceid, ec2instance['instanceId'], device)

    while True:
      statuscheck = ec2api.get_all_network_interfaces(filters = {
        'network-interface-id' : cliargs.networkinterfaceid
      }).pop()

      if 'in-use' == statuscheck.status:
        break

      time.sleep(2)

    # just because aws says it's available, doesn't mean the os sees it yet

    if cliargs.wait:
      while True:
        if 0 == subprocess.call('grep -q ^1$ /sys/class/net/%s/carrier' % devices[device], shell=True, stdout=TASK_STDOUT, stderr=TASK_STDERR):
          break

        time.sleep(2)

    if cliargs.verbose > 0:
      sys.stderr.write('attached (%s)\n' % device)
  else:
    device = mounted.attachment.device_index

  subnet = vpcapi.get_all_subnets([ mounted.subnet_id.encode('ascii') ]).pop()
  subnet_network = ipaddress.ip_network(subnet.cidr_block)
  subnet_hosts = list(subnet_network.hosts())

  if None != cliargs.env_file:
    f = open(cliargs.env_file, 'w')
    f.write('%sDEVICEN=%s\n' % ( cliargs.env_prefix, device ))
    f.write('%sDEVICE=%s\n' % ( cliargs.env_prefix, devices[device] ))
    f.write('%sCIDR=%s\n' % ( cliargs.env_prefix, subnet.cidr_block ))
    f.write('%sGATEWAY=%s\n' % ( cliargs.env_prefix, subnet_hosts[0] ))
    f.write('%sIP0=%s\n' % ( cliargs.env_prefix, mounted.private_ip_address ))
    f.close()

elif 'detach' == cliargs.action:
  if False != mounted:
    if cliargs.verbose > 1:
      sys.stderr.write('detaching (%s)...\n' % mounted.attachment.device_index)

    ec2api.detach_network_interface(mounted.attachment.id.encode('ascii'))

    while True:
      statuscheck = ec2api.get_all_network_interfaces(filters = {
        'network-interface-id' : mounted.id.encode('ascii')
      }).pop()

      if 'available' == statuscheck.status:
        break

      time.sleep(2)

    if cliargs.verbose > 0:
      sys.stderr.write('detached (%s)\n' % mounted.attachment.device_index)
