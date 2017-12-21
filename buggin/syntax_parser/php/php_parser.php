#!/usr/bin/env php
<?php
require __DIR__ . '/vendor/autoload.php';
use PhpParser\Error;
use PhpParser\NodeDumper;
use PhpParser\ParserFactory;
use PhpParser\NodeTraverser;
use PhpParser\Node;
use PhpParser\NodeVisitorAbstract;


class MyNodeVisitor extends NodeVisitorAbstract
{
	public $FunctionNodes = [];

	public function leaveNode(Node $node)
	{
		if ($node instanceof PhpParser\Node\Stmt\ClassMethod)
		{
			$start = $node->getAttribute('startLine');
			$end = $node->getAttribute('endLine');
			$func = array_slice($this->File, $start - 1, ($end - $start + 1));
			$this->FunctionNodes[$node->name] = $func;
		}
	}

	public function enterNode(Node $node)
	{
		if ($node instanceof PhpParser\Node\Stmt\ClassMethod)
		{
			return NodeTraverser::DONT_TRAVERSE_CHILDREN;
		}
	}

	public function GetFunctionNodes()
	{
		return $this->FunctionNodes;
	}

	public function SetFile($f)
	{
		$this->File = explode("\n", $f);
	}
}

$shortOpts = 'f:o:';
$longOpts = [
	'file:',
	'output:'
];

$opts = getopt($shortOpts, $longOpts);
$file = trim($opts['f']);
if (!isset($opts['o']))
{
	//TODO print usage
	throw new Exception('Must supply output file');
}
if (!isset($opts['f']))
{
	//TODO print usage
	throw new Exception('Must supply input file');
}
if (!file_exists($file))
{
	// TODO print usage
	throw new Exception('File does not exist: ' . $file);
}

$phpContents = file_get_contents($file);
$outputJSON = trim($opts['o']);

// TODO: variable php version
// other options:
// PREFER_PHP7
// ONLY_PHP7
// ONLY_PHP5
$parser = (new ParserFactory)->create(ParserFactory::PREFER_PHP7);
$traverser = new NodeTraverser();
$visitor =  new MyNodeVisitor();
$visitor->SetFile($phpContents);
$traverser->addVisitor($visitor);
try {
    $ast = $parser->parse($phpContents);
} catch (Error $error) {
    echo "Parse error: {$error->getMessage()}\n";
    return;
}

$dumper = new NodeDumper();
$traverser->traverse($ast);
$functionNodes = $visitor->GetFunctionNodes();
//print_r($functionNodes);
file_put_contents($outputJSON, json_encode($functionNodes));
//echo json_encode($functionNodes);