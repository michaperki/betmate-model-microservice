// Simple Node.js script to test connection to the API Gateway
const fetch = require('node-fetch');

// API Gateway endpoints
const WDL_URL = 'https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/wdl';
const TOP_MOVES_URL = 'https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/top-moves';
const MOVE_ANALYSIS_URL = 'https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/move-analysis';

// Test parameters
const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const TEST_MOVE = 'e4';
const TEST_N = 3;

// Test WDL endpoint
async function testWdl() {
  console.log('Testing WDL endpoint...');
  try {
    const response = await fetch(`${WDL_URL}?fen=${encodeURIComponent(TEST_FEN)}`);
    console.log('Status:', response.status);
    console.log('Headers:', response.headers);
    const data = await response.json();
    console.log('Data:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test Top Moves endpoint
async function testTopMoves() {
  console.log('\nTesting Top Moves endpoint...');
  try {
    const response = await fetch(`${TOP_MOVES_URL}?fen=${encodeURIComponent(TEST_FEN)}&n=${TEST_N}`);
    console.log('Status:', response.status);
    console.log('Headers:', response.headers);
    const data = await response.json();
    console.log('Data:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test Move Analysis endpoint
async function testMoveAnalysis() {
  console.log('\nTesting Move Analysis endpoint...');
  try {
    const response = await fetch(`${MOVE_ANALYSIS_URL}?fen=${encodeURIComponent(TEST_FEN)}&move=${TEST_MOVE}`);
    console.log('Status:', response.status);
    console.log('Headers:', response.headers);
    const data = await response.json();
    console.log('Data:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Run all tests
async function runTests() {
  await testWdl();
  await testTopMoves();
  await testMoveAnalysis();
}

runTests();