#!/usr/bin/perl -w
use File::Find ();
use File::Copy;
use Date::Parse;
use Getopt::Std;

my %options = ();

getopts('c', \%options);
my $targetDir;

# Process gallery_config.py
# Yes, I know I'm a terrible person
$configPath = shift;
$userName = shift;
die "usage: whatsnewgen.pl [-c] config username\n" unless $configPath and $userName;
open CONFIG, $configPath or die "Couldn't open $configPath: $!\n";
while( <CONFIG> )
{
  if( m/'$userName'\s*:\s*{/ )
  {
    while( <CONFIG> )
    {
      if( m/'img_prefix'\s*:\s*"([^"]+)"/i )
      {
        $targetDir = $1;
        last;
      }
    }
    last;
  }
}
close CONFIG;
my $whatsNew = $targetDir . "/whatsnew.txt";

my $whatsNewBackup;

my $showAfterTime = 0;

#deal with the existing file
if( -e $whatsNew )
{
  $whatsNewBackup = $whatsNew . ".tmp";
  die "$whatsNewBackup already exists.\n" if (-e $whatsNewBackup);

  die "Couldn't create $whatsNewBackup: $!\n"
    unless move( $whatsNew, $whatsNewBackup );

#find the most recent timestamp
  open WHATSNEWBACKUP, $whatsNewBackup;
  while(<WHATSNEWBACKUP>)
  {
    if( m/^DATE (.*)$/ )
    {
      my $time = str2time($1);
      $showAfterTime = $time if( $time > $showAfterTime );
    }
  }
  close WHATSNEWBACKUP;
}


# Set the variable $File::Find::dont_use_nlink if you're using AFS,
# since AFS cheats.

# for the convenience of &wanted calls, including -eval statements:
use vars qw/*name *dir *prune/;
*name   = *File::Find::name;
*dir    = *File::Find::dir;
*prune  = *File::Find::prune;

sub wanted;

my %lastModifiedByDir = ();



# Traverse desired filesystems
File::Find::find({wanted => \&wanted}, $targetDir);

#flip flop the hashtable and strip out the value that don't matter
my %dirByModifiedTime = ();
foreach my $d (keys %lastModifiedByDir)
{
  if( $lastModifiedByDir{$d} > $showAfterTime )
  {
    $dirByModifiedTime{$lastModifiedByDir{$d}} = $d;
  }
}

#print out the dirs in sorted order
open( WHATSNEW, '>', $whatsNew )or die "Couldn't open $whatsNew for writing: $!\n";
  
foreach my $mt (sort {$b <=> $a} keys %dirByModifiedTime)
{
  print WHATSNEW "START\n";
  print WHATSNEW "DATE " . localtime($mt) . "\n";
  print WHATSNEW "DIR " . $dirByModifiedTime{$mt} . "\n";
  print WHATSNEW "END\n";
}
if( defined $whatsNewBackup )
{
  open BACKUP, $whatsNewBackup;
  print WHATSNEW while(<BACKUP>);
  close BACKUP;
}
close WHATSNEW;
unlink $whatsNewBackup if( $whatsNewBackup );


exit;


sub wanted {
my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,$atime,$mtime,$ctime);

  return unless (($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,$atime,
                  $mtime, $ctime) = lstat($_));
  return unless $name =~ m/\.(jpg|jpeg|avi)$/i;
  return if m/^\./i;
  my $useTime;
  if( exists $options{'c'} )
  {
    $useTime = $ctime;
  }
  else
  {
    $useTime = $mtime;
  }

  if( -f $_ )
  {
    my $pattern = "^" . quotemeta($targetDir) . "/?";
    my $shortDir = $dir;
    $shortDir =~ s/$pattern//o;
    if( exists $lastModifiedByDir{$shortDir} )
    {
      $lastModifiedByDir{$shortDir} = $useTime
        if( $lastModifiedByDir{$shortDir} < $useTime );
    }
    else
    {
      $lastModifiedByDir{$shortDir} = $useTime;
    }
  }
}

