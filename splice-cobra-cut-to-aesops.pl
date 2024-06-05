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

my ($cobra_file, $aesops_file) = @ARGV;

sub get_json_from_file($file) {
    my $guts = path($file)->slurp_raw;
    my $json = eval { decode_json($guts) };
    unless ( defined $json ) {
        warn "Error decoding JSON: $@\n";
        return undef;
    }
    return $json;
}

my $cobra = get_json_from_file($cobra_file) or die "Error reading Cobra data\n";
my $aesops = get_json_from_file($aesops_file) or die "Error reading Aesops data\n";


my (%cobra_by_rank, %aesops_by_rank);
my (%cobra_by_id, %aesops_by_id);

for my $player ( $cobra->{players}->@* ) {
    my $p_struct = {
        id => $player->{id},
        rank => $player->{rank},
        name => $player->{name},
    };

    $cobra_by_rank{$player->{rank}} = $p_struct;
    $cobra_by_id{$player->{id}} = $p_struct;
}

for my $player ( $aesops->{players}->@* ) {
    my $p_struct = {
        id => $player->{id},
        rank => $player->{rank},
        name => $player->{name},
    };

    $aesops_by_rank{$player->{rank}} = $p_struct;
    $aesops_by_id{$player->{id}} = $p_struct;
}

for my $rank ( 1 .. 16 ) {
    say sprintf("Swiss rank %d: Cobra ID %d (%s) -> Aesops ID %d (%s)",
        $rank,
        $cobra_by_rank{$rank}{id}, $cobra_by_rank{$rank}{name},
        $aesops_by_rank{$rank}{id}, $aesops_by_rank{$rank}{name},
    );
}

# update elim players
$aesops->{eliminationPlayers} = $cobra->{eliminationPlayers};
for my $p ( $aesops->{eliminationPlayers}->@* ) {
    my $orig_rank = $p->{seed};
    my $c_player = $cobra_by_rank{$orig_rank};
    my $a_player = $aesops_by_rank{$orig_rank};
    say sprintf("Cut rank %d: mapping %d (%s) to %d (%s)",
        $p->{rank},
        $p->{id}, $c_player->{name},
        $a_player->{id}, $a_player->{name},
    );

    $p->{id} = $a_player->{id};
}

# # splice elim games
my $a_rounds = $aesops->{rounds};
my $c_rounds = $cobra->{rounds};

my $r_no = -1;
for my $r ( $c_rounds->@* ) {
    $r_no++;
    if (! $r->[0]{eliminationGame} ) {
        next;
    }
    my @new_tables;
    for my $t ( $r->@* ) {
        my $old_p1 = { $t->{player1}->%* };
        my $old_p2 = { $t->{player2}->%* };
        $t->{player1}{id} = $aesops_by_rank{
            $cobra_by_id{$old_p1->{id}}{rank}
        }{id};
        $t->{player2}{id} = $aesops_by_rank{
            $cobra_by_id{$old_p2->{id}}{rank}
        }{id};

        my $p1_is_runner = $old_p1->{role} eq 'runner';
        my $p1_is_winner = !! $old_p1->{winner};

        say sprintf("R %d, T %d: P1 %s %d -> %d; P2 %s %d -> %d",
            $r_no, $t->{table},
            $cobra_by_id{$old_p1->{id}}{name}, $old_p1->{id}, $t->{player1}{id},
            $cobra_by_id{$old_p2->{id}}{name}, $old_p2->{id}, $t->{player2}{id},
        );
        my $aesops_table = {
            tableNumber => $t->{table},
            eliminationGame => JSON::MaybeXS::true,
            runnerPlayer => $p1_is_runner ? $t->{player1}{id} : $t->{player2}{id},
            corpPlayer => (! $p1_is_runner) ? $t->{player1}{id} : $t->{player2}{id},
            winner_id => $p1_is_winner ? $t->{player1}{id} : $t->{player2}{id},
            loser_id => (! $p1_is_winner) ? $t->{player1}{id} : $t->{player2}{id},
        };
        push @new_tables, $aesops_table;
    }

    push $a_rounds->@*, \@new_tables;
}

my $jcodec = JSON::MaybeXS->new( canonical => 1, ascii => 1, pretty => 1);
say $jcodec->encode($aesops);
