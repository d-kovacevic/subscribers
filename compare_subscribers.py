#!/usr/bin/python

import xmltodict
import re
import subprocess
import argparse

RESET_MODEM_SCRIPT = './reset_modem_test.sh'
#RESET_MODEM_SCRIPT = '/home/h-bol/reset_modem.sh'


def print_title(text, char="="):
    print (len(text) + 4) * char
    print "| " + text + " |"
    print (len(text) + 4) * char
    return


def print_array_csv(list, separator=","):
    print separator.join(list)
    print


def print_plain(text):
    print text


def check_int_range(value):
    ivalue = int(value)
    if ivalue <= 0 or ivalue > 1000:
         raise argparse.ArgumentTypeError("%s is not in the range 1 to 1000" % value)
    return ivalue


def get_diff_ips(file_b, file_a):

    with open(file_b) as fd:
        subscribers_b = xmltodict.parse(fd.read())
        subscribers_b_list = subscribers_b['rpc-reply']['subscribers-information']['subscriber']
        if type(subscribers_b_list) is dict:
            subscribers_b_list = [subscribers_b_list]

    with open(file_a) as fd:
        subscribers_a = xmltodict.parse(fd.read())
        subscribers_a_list = subscribers_a['rpc-reply']['subscribers-information']['subscriber']
        if type(subscribers_a_list) is dict:
            subscribers_a_list = [subscribers_a_list]

    ip_addr_b = []
    ip_addr_a = []

    for subscriber in subscribers_b_list:
        if re.match('pp0', subscriber['interface']):
            ip_addr_b.append(subscriber['ip-address'])

    for subscriber in subscribers_a_list:
        if re.match('pp0', subscriber['interface']):
            ip_addr_a.append(subscriber['ip-address'])

    ip_addr_diff = list(set(ip_addr_b) - set(ip_addr_a))

    return ip_addr_diff


def get_chunks(l, n):
    for i in range(0, len(l), n):
        yield(l[i:i + n])


def get_diff_ips_vod(file_b, file_a):

    ip_addr_diff = get_diff_ips(file_b, file_a)
    ip_addr_diff_vod = []
    ip_without_mgmt = []

    for ip_addr_chuck in get_chunks(ip_addr_diff, 200):

        print_title("Modem public IP addresses to reboot (%d modems):" % len(ip_addr_chuck))
        print_array_csv(ip_addr_chuck)

        cmd = ['find_ipaddress.rb'] + ip_addr_chuck

        (stdout, stderr) = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()

        for line in stdout.split('\n'):
            if not re.match('orderid', line):
                if len(line.split(',')) > 2:
                    if line.split(',')[2] == '':
                        ip_without_mgmt.append(line.split(',')[0])
                    else:
                        ip_addr_diff_vod.append(line.split(',')[2])

    print_title("Modem VOD IP addresses to reboot (%d modems):" % len(ip_addr_diff_vod))
    print_array_csv(ip_addr_diff_vod)

    print_title("Order ID's without management IP (%d modems):" % len(ip_without_mgmt))
    print_array_csv(ip_without_mgmt)

    return ip_addr_diff_vod


def reboot_modems(ips_vod, batch, connect_script):
    for index, ip_addr_chuck in enumerate(get_chunks(ips_vod, batch)):
        while True:
            print_plain("\n")
            print_title("The list of modems to reboot in batch #%d (%d modems)" % (index + 1, len(ip_addr_chuck)))
            print_array_csv(ip_addr_chuck)

            answer = raw_input("\nDo you want to proceed with rebooting batch #%d? (y|n):" % (index + 1))
            if answer.lower() == "yes" or answer.lower() == "y":

                cmd = [connect_script, 'tele2tftp01asd2', RESET_MODEM_SCRIPT] + ip_addr_chuck

                (stdout, stderr) = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
                print_plain(stdout)
                break
            elif answer.lower() == "no" or answer.lower() == "n":
                exit()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Compare and reboot missing PPP subscribers')
    parser.add_argument('-sb', '--subscribers-before', help='XLM list of subscriber before (show subscribers | display xml)', required=True)
    parser.add_argument('-sa', '--subscribers-after', help='XLM list of subscriber after (show subscribers | display xml)', required=True)
    parser.add_argument('-n', '--modem-batch', help='Number of modems to reboot in one batch', type=check_int_range, default=100)
    parser.add_argument('-c', '--connect-script', help='Connection script to the tftp server', default="ssh_askpass.sh")
    return vars(parser.parse_args())


def main():
    args = parse_arguments()
    ips_vod = get_diff_ips_vod(args['subscribers_before'], args['subscribers_after'])
    reboot_modems(ips_vod, args['modem_batch'], args["connect_script"])

if __name__ == "__main__":
    main()