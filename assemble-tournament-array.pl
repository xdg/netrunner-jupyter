#!/usr/bin/env perl
use v5.28;
use strict;
use warnings;
use utf8;
use open qw/:std :utf8/;
use feature 'signatures';
no warnings 'experimental::signatures';

use Path::Tiny;

for my $line (@ARGV) {
    chomp $line;
    my $file = path($line)->basename;
    next unless $file =~ /-(?:aesops|cobra)\.json$/;
    my ( $prefix, $source ) = $file =~ m{^(.+?)-(aesops|cobra)};
    say qq{["$prefix", "$source"],};
}

