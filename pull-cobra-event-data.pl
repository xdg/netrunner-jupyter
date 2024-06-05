#!/usr/bin/env perl
use v5.28;
use strict;
use warnings;
use utf8;
use open qw/:std :utf8/;
use feature 'signatures';
no warnings 'experimental::signatures';

use Encode;
use HTTP::Tiny;
use JSON::MaybeXS;
use Path::Tiny;
require Encode::Detect;

my ( $cobra, $abr, $event ) = @ARGV;

die "usage: $0 <cobra-id> <abr-id> <event-name>\n"
  unless $cobra && $abr && length($event);

my $cobra_json = getCobra($cobra)
  or die "Failed to get Cobra data\n";

say "Fetched Cobra data";
my $date = $cobra_json->{date} // "0000-00-00";

my $abr_json = getABR($abr)
  or die "Failed to get ABR data\n";

say "Fetched ABR data";

$event =~ s{\s+}{-}g;

my $jcodec = JSON::MaybeXS->new( canonical => 1, ascii => 1 );

path("$date-$event-cobra.json")->spew_utf8( $jcodec->encode($cobra_json) );
path("$date-$event-abr.json")->spew_utf8( $jcodec->encode($abr_json) );

sub getCobra ($id) {
    return getJSON( $id, "https://tournaments.nullsignal.games/tournaments/%d.json" );
}

sub getABR ($id) {
    return getJSON( $id, "https://alwaysberunning.net/api/entries?id=%d.json" );
}

sub getJSON ( $id, $template ) {
    my $url = sprintf( $template, $id );
    my $resp = HTTP::Tiny->new->get( $url );

    if ( !$resp->{success} ) {
        warn "Error getting $url: $resp->{reason}\n";
        return undef;
    }

    my $json = eval { decode_json($resp->{content}) };
    unless ( defined $json ) {
        warn "Error decoding JSON: $@\n";
        return undef;
    }
    return $json;
}

