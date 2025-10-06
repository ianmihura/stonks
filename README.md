# Stonks!

Stonks is a betting game inspired by poker and stock market trading. The game was invented by Ian Mihura with no copyright associated. All the fun you have and the money you loose are yours alone.

This repo includes a work-in-progress implementation for the game. 

It was especially useful for fine tuning the game mechanics and strategy. The plan is to make it into a working cli interactive game.

# Rules of the game:

This game uses an English deck and poker chips.

### Players

Played with at least 2 players, more players make the game more interesting.

The dealer/house is chosen at random and changes every turn.

### Chips

Players start with at least $100 worth in chips, payable in sums of 1, 5 and 10. Recommended start with about $500 stack. The house has practically unlimited chips.

### Deal

Players get 6 cards each, and should always have 6 cards at play (including cards in their hand and in active positions). Discarded cards are replaced by drawing from the deck.

If the deck runs out, re-shuffle the discarded pile.

### Overview

Players take turns to negotiate bets with each other. Once everyone has played and the turn comes back to the dealer (and after they play), they draw a card from the deck, revealing how much the asset price has moved. Players must then pay their obligations, and another round starts. 

Players also take turns to start each round. Rounds run clockwise, and the player to the left of the dealer/house is the first to start.

Last player standing wins the game.

### Rounds & betting

In their turn a player can do any number of the following actions:

- Open a position: a player can either
    - Announce an intention:
        
        Players announce their intention to open a position by placing a card on the table. If they play a red card they are short (expect the price to go down), if the card is black they are long. Cards played cannot be called back.
        
    - Match a position:
        
        Players take up existing bets by playing a card of the opposite suit on top of another previously announced intention. The size of the position is always the smallest card between the two. Both cards are normally set in-front of the buyer.
        
- “Double-down” on an existing position by playing another card on that pile, potentially rising the size of the position. The position size will always be the sum of the lowest side. Example: red cards 2 and 4 (short) against a black card 8 (long), the position is worth 6 (small) for both sides.
- Close a position (see section below).
- Pass (no action).

Some notes:

- Play against the house: if the round ends and no other player was willing to take up a bet, the house will take it up, but the player must pay the house $1 per round for this service. The position size is the value of the player’s card: the house does not play a card.
- Players are free to say whatever they want, but played cards and paid chips cannot be taken back.
- Players can open as many positions as they want.

### Closing a bet

To close a bet, a player must “buy back” their position with one (or more) cards from their hand. The cards they use must:

- Color opposite from their position
- Add up to a number equal or greater than the smallest card of the position. Face cards are worth 10.
    - Example: a red card 4 (short) against a black card 8 (long). To buy back the position, any player must play a card(s) of value that add to 4 or more, of the corresponding color.
- Exception: players can use any As to buy back a position, regardless of color and size.

If a player cannot buy back a position with cards, they can pay the house for them to close the position: house charges $5 for a small position and $10 for a big position. Alternatively, the counter-party of the position can accept any compensation to do the same.

When a position is closed, all cards from the position are discarded, and players immediately draw new cards to replace them.

### Market movement

The market can move *up* or *down*, and *big* or *small*.

The dealer draws a card from the deck: this card defines the market movement. Suit defines direction and number defines magnitude:

- Black suit: price goes up (long positions are paid).
- Red suit: price goes down (short positions are paid).
- Small card (As - 6s): moves small.
- Big card (7s - Ks): moves big.

### Payment

The payments of each position depend on the position size and the market move:

- If the position is small and
    - Market moves small: pay $3
    - Market moves big: pay $5
- If the position is big and
    - Market moves small: pay $5
    - Market moves big: pay $10
- Special case: If the position is a face card (Js - Ks), and market moves by a face card: pay $20 (stonks!)

|  | Small position | Big position | Position is a face card |
| --- | --- | --- | --- |
| Small price movement | 3 | 5 | 5 |
| Big price movement | 5 | 10 | 10 |
| Price moves by a face card | 5 | 10 | 20 (stonks!) |

### Blinds

In each round, the player to the right of the dealer has to pay a blind, usually the size of a ‘big’ payout, to the middle pot. This pot grows until there’s a ‘Stonk!’ payout (see payment section for details), in which case the winner of the position takes the pot. If there’s more than one winner, the pot is split between them. If the house is a winner, they do not take the pot.

### Shorter game

To speed up the endgame, the house may charge a fixed fee per round (rake) to all players.

### Variation: free-for-all

Instead of taking turns to make bets, players are free to bet each other in any order. A round finishes when every player is satisfied with their positions.

Fair play note: when a player is in negotiations to close a position, the other player cannot double-down on the position to increase its size.
