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
use IO::Prompt::Tiny 'prompt';
require Encode::Detect;

my ( $aesops, $abr, $event, $date ) = @ARGV;

die "usage: $0 <aesops-id> <abr-id> <event-name> <date>\n"
  unless $aesops && $abr && length($event);

my $aesops_json = getaesops($aesops)
  or die "Failed to get aesops data\n";

say "Fetched aesops data";
if (! defined $aesops_json->{date}) {
    if (!defined $date) {
        $date = prompt("Date?");
        chomp $date;
    }
    $aesops_json->{date} = $date;
}

my $abr_json = getABR($abr);
if (! defined $abr_json) {
    $abr_json = [{"user_import_name" => "NONE", "user_name" =>  "NONE"}];
    say "Couldn't fetch ABR data; proxied with empty data file";
} else {
    say "Fetched ABR data";
}

$event =~ s{\s+}{-}g;

my $jcodec = JSON::MaybeXS->new( canonical => 1, ascii => 1 );

path("$date-$event-aesops.json")->spew_utf8( $jcodec->encode($aesops_json) );
path("$date-$event-abr.json")->spew_utf8( $jcodec->encode($abr_json) );

sub getaesops ($id) {
    return getJSON( $id, "https://www.aesopstables.net/%d/abr_export" );
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

