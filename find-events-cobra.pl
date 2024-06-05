#!/usr/bin/env perl
use v5.28;
use strict;
use warnings;
use utf8;
use open qw/:std :utf8/;
use feature 'signatures';
no warnings 'experimental::signatures';

use HTTP::Tiny;
use JSON::MaybeXS;

my ($start, $stop) = @ARGV;

die "usage: $0 <first> <last>\n" unless $start && $stop && ( $stop >= $start );

STDOUT->autoflush(1);

for my $n ($start .. $stop ) {
    my $json = getCobra($n);
    my $link = sprintf("https://tournaments.nullsignal.games/tournaments/%d/players/standings", $n);
    printf("%d -> %s -> %s\n", $n, $json->{name}, $link);
}

sub getCobra($id) {
    my $resp = HTTP::Tiny->new->get(
        sprintf("https://tournaments.nullsignal.games/tournaments/%d.json", $id)
    );

    if (! $resp->{success} ) {
        return {name => "failed: $resp->{reason}"};
    }

    my $body = $resp->{content};
    my $json = eval { decode_json($body) };
    unless (defined $json) {
        return {name => "failed to decode JSON"};
    }
    return $json
}


