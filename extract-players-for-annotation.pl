#!/usr/bin/env perl
use v5.28;
use strict;
use warnings;
use utf8;
use open qw/:std :utf8/;
use feature 'signatures';
no warnings 'experimental::signatures';

use Path::Tiny;
use JSON::MaybeXS;
use Tie::IxHash;

my $file = shift;

my $json = decode_json(path($file)->slurp_raw);

my %map;
for my $p ( $json->{players}->@* ) {
    my %struct;
    tie %struct, "Tie::IxHash", 
        name =>  $p->{name},
        runnerIdentity => $p->{runnerIdentity},
        corpIdentity => $p->{corpIdentity};

    $map{$p->{id}} = \%struct;
}

my $jcodec = JSON::MaybeXS->new( ascii => 1, pretty => 1 );
say $jcodec->encode(\%map);
