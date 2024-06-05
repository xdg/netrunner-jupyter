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

my ($aesops_file) = @ARGV;

sub get_json_from_file($file) {
    my $guts = path($file)->slurp_raw;
    my $json = eval { decode_json($guts) };
    unless ( defined $json ) {
        warn "Error decoding JSON: $@\n";
        return undef;
    }
    return $json;
}

my $aesops = get_json_from_file($aesops_file) or die "Error reading Aesops data\n";

my @abr;
for my $player ( $aesops->{players}->@* ) {
    my $p_struct = {
        user_name => $player->{name},
        user_import_name => $player->{name},
    };
    push @abr, $p_struct;
}

my $jcodec = JSON::MaybeXS->new( canonical => 1, ascii => 1, pretty => 1);
say $jcodec->encode(\@abr);
