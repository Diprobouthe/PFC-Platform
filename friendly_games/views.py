from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import json
import logging
from teams.models import Player, Team
from .models import FriendlyGame, FriendlyGamePlayer, PlayerCodename, FriendlyGameStatistics
from pfc_core.session_utils import CodenameSessionManager

logger = logging.getLogger(__name__)


def create_game(request):
    """
    Create a new friendly game with player selection and codename verification.
    This is the enhanced replacement for the unused 'Start Match' button.
    """
    # Get logged-in user's codename from session
    session_codename = CodenameSessionManager.get_logged_in_codename(request)
    
    if request.method == 'POST':
        # Handle game creation logic here
        game_name = request.POST.get('game_name', 'Friendly Game')
        creator_codename = request.POST.get('creator_codename', '').strip()
        creator_position = request.POST.get('creator_position', '').strip()
        black_team_players = request.POST.get('black_team_players', '[]')
        white_team_players = request.POST.get('white_team_players', '[]')
        
        try:
            # Parse player IDs from JSON
            black_player_ids = json.loads(black_team_players) if black_team_players else []
            white_player_ids = json.loads(white_team_players) if white_team_players else []
            
            # Create the game
            game = FriendlyGame.objects.create(name=game_name)
            
            # Validate creator codename if provided
            creator_player = None
            if creator_codename:
                try:
                    creator_player_codename = PlayerCodename.objects.get(codename=creator_codename)
                    creator_player = creator_player_codename.player
                except PlayerCodename.DoesNotExist:
                    messages.warning(request, f'Invalid creator codename: {creator_codename}')
            
            # Add black team players
            for player_id in black_player_ids:
                try:
                    player = Player.objects.get(id=player_id)
                    # Check if this player is the creator and validate them
                    codename_verified = False
                    provided_codename = ''
                    position = 'MILIEU'  # Default position
                    
                    # Check if this is the creator player (regardless of codename validation)
                    if creator_player and player.id == creator_player.id:
                        # Use creator's specified position if provided
                        if creator_position:
                            position = creator_position.upper()
                        
                        # Handle codename verification separately
                        codename_verified = True
                        provided_codename = creator_codename
                    
                    FriendlyGamePlayer.objects.create(
                        game=game,
                        player=player,
                        team='BLACK',
                        position=position,
                        provided_codename=provided_codename,
                        codename_verified=codename_verified
                    )
                except Player.DoesNotExist:
                    messages.warning(request, f'Player with ID {player_id} not found')
            
            # Add white team players
            for player_id in white_player_ids:
                try:
                    player = Player.objects.get(id=player_id)
                    # Check if this player is the creator and validate them
                    codename_verified = False
                    provided_codename = ''
                    position = 'MILIEU'  # Default position
                    
                    # Check if this is the creator player (regardless of codename validation)
                    if creator_player and player.id == creator_player.id:
                        # Use creator's specified position if provided
                        if creator_position:
                            position = creator_position.upper()
                        
                        # Handle codename verification separately
                        codename_verified = True
                        provided_codename = creator_codename
                    
                    FriendlyGamePlayer.objects.create(
                        game=game,
                        player=player,
                        team='WHITE',
                        position=position,
                        provided_codename=provided_codename,
                        codename_verified=codename_verified
                    )
                except Player.DoesNotExist:
                    messages.warning(request, f'Player with ID {player_id} not found')
            
            # Update game validation status
            game.update_validation_status()
            
            # Create success message with creator validation info
            total_players = len(black_player_ids) + len(white_player_ids)
            success_msg = f'Friendly game "{game.name}" created successfully with {total_players} players!'
            
            if creator_player:
                success_msg += f' Creator validated as {creator_player.name}.'
            elif creator_codename:
                success_msg += f' Creator codename "{creator_codename}" not found - no validation.'
            
            success_msg += f' Match Number: {game.match_number}'
            
            messages.success(request, success_msg)
            return redirect('friendly_games:game_detail', game_id=game.id)
            
        except json.JSONDecodeError:
            messages.error(request, 'Invalid player selection data')
        except Exception as e:
            messages.error(request, f'Error creating game: {str(e)}')
    
    # Get all teams with their players for selection
    teams = Team.objects.all().prefetch_related('players')
    
    # Auto-detect logged-in player and add to black team
    auto_selected_player = None
    if session_codename:
        try:
            # Find player by codename
            player_codename = PlayerCodename.objects.get(codename=session_codename)
            auto_selected_player = player_codename.player
        except PlayerCodename.DoesNotExist:
            # If no exact codename match, try to find by name similarity
            try:
                auto_selected_player = Player.objects.get(name__iexact=session_codename)
            except Player.DoesNotExist:
                pass
    
    context = {
        'teams': teams,
        'team_name': request.session.get('team_name', 'Guest'),
        'auto_selected_player': auto_selected_player,
        'session_codename': session_codename,
    }
    
    return render(request, 'friendly_games/create_game.html', context)


def game_detail(request, game_id):
    """Display details of a friendly game"""
    game = get_object_or_404(FriendlyGame, id=game_id)
    players = game.players.all().select_related('player', 'player__team')
    
    context = {
        'game': game,
        'players': players,
    }
    
    return render(request, 'friendly_games/game_detail.html', context)


def activate_game(request, game_id):
    """Activate a friendly game to start playing"""
    game = get_object_or_404(FriendlyGame, id=game_id)
    
    if game.status == 'READY':
        game.status = 'ACTIVE'
        game.save()
        messages.success(request, f'Game "{game.name}" is now active!')
    
    return redirect('friendly_games:game_detail', game_id=game.id)


def submit_score(request, game_id):
    """Submit scores for a friendly game"""
    game = get_object_or_404(FriendlyGame, id=game_id)
    
    if request.method == 'POST':
        black_score = int(request.POST.get('black_score', 0))
        white_score = int(request.POST.get('white_score', 0))
        
        # Validate scores
        if black_score < 0 or white_score < 0:
            messages.error(request, 'Scores cannot be negative.')
            return redirect('friendly_games:submit_score', game_id=game.id)
        
        # Add maximum score validation (like tournament matches)
        if black_score > 13 or white_score > 13:
            messages.error(request, 'Scores cannot exceed 13 points.')
            return redirect('friendly_games:submit_score', game_id=game.id)
        
        if black_score == white_score:
            messages.error(request, 'Scores cannot be tied. One team must win.')
            return redirect('friendly_games:submit_score', game_id=game.id)
        
        game.black_team_score = black_score
        game.white_team_score = white_score
        game.status = 'COMPLETED'
        game.save()
        
        # ===== RATING SYSTEM INTEGRATION =====
        # Update player ratings after successful friendly game completion
        # This is completely separate from game completion and won't affect it if it fails
        try:
            from matches.rating_integration import update_friendly_game_ratings
            rating_result = update_friendly_game_ratings(game)
            if rating_result["success"]:
                logger.info(f"Friendly game {game.id} rating updates: {rating_result.get('reason', 'completed successfully')}")
            else:
                logger.warning(f"Friendly game {game.id} rating updates failed: {rating_result.get('reason', 'unknown error')}")
        except Exception as e:
            logger.error(f"Rating system error for friendly game {game.id}: {e}")
            # Continue with normal game completion - rating failures don't break games
        # ===== END RATING SYSTEM INTEGRATION =====
        
        messages.success(request, f'Scores submitted! Black: {black_score}, White: {white_score}')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    context = {
        'game': game,
    }
    
    return render(request, 'friendly_games/submit_score.html', context)


def game_list(request):
    """List all friendly games"""
    games = FriendlyGame.objects.all().order_by('-created_at')
    
    context = {
        'games': games,
    }
    
    return render(request, 'friendly_games/game_list.html', context)



def join_game(request):
    """
    Join a friendly game using match number.
    Players can select team, position, and optionally provide codename for stats.
    """
    if request.method == 'POST':
        match_number = request.POST.get('match_number', '').strip()
        team = request.POST.get('team')
        position = request.POST.get('position', 'MILIEU')
        player_name = request.POST.get('player_name', '').strip()
        codename = request.POST.get('codename', '').strip()
        
        # Validate required fields
        if not match_number or not team or not player_name:
            messages.error(request, 'Match number, team, and player name are required.')
            return render(request, 'friendly_games/join_game.html')
        
        try:
            # Find the game by match number
            game = FriendlyGame.objects.get(match_number=match_number)
            
            # Check if game is expired
            if game.is_expired():
                game.status = 'EXPIRED'
                game.save()
                messages.error(request, f'Match #{match_number} has expired.')
                return render(request, 'friendly_games/join_game.html')
            
            # Check if game is still accepting players
            if game.status not in ['WAITING_FOR_PLAYERS', 'DRAFT']:
                messages.error(request, f'Match #{match_number} is no longer accepting players.')
                return render(request, 'friendly_games/join_game.html')
            
            # Check team capacity (max 3 players per team)
            team_count = game.players.filter(team=team).count()
            if team_count >= 3:
                messages.error(request, f'{team.title()} team is full (3 players maximum).')
                return render(request, 'friendly_games/join_game.html')
            
            # Find or create a special team for friendly games
            friendly_team, created = Team.objects.get_or_create(
                name="Friendly Games",
                defaults={'pin': '000000'}  # Special PIN for friendly games team
            )
            
            # Find or create player
            player, created = Player.objects.get_or_create(
                name=player_name,
                defaults={'team': friendly_team}
            )
            
            # Check if player is already in this game
            if game.players.filter(player=player).exists():
                messages.warning(request, f'{player_name} is already in this game.')
                return redirect('friendly_games:game_detail', game_id=game.id)
            
            # Verify codename if provided
            codename_verified = False
            if codename:
                try:
                    player_codename = player.codename_profile
                    codename_verified = (codename == player_codename.codename)
                except PlayerCodename.DoesNotExist:
                    codename_verified = False
            
            # Add player to game
            FriendlyGamePlayer.objects.create(
                game=game,
                player=player,
                team=team,
                position=position,
                provided_codename=codename,
                codename_verified=codename_verified
            )
            
            # Update game validation status
            game.update_validation_status()
            
            # Success message
            verification_msg = " (Stats will be recorded)" if codename_verified else " (No stats - codename not verified)" if codename else ""
            messages.success(request, f'{player_name} joined {team.title()} team as {position}{verification_msg}')
            
            return redirect('friendly_games:game_detail', game_id=game.id)
            
        except FriendlyGame.DoesNotExist:
            messages.error(request, f'No game found with match number #{match_number}')
        except Exception as e:
            messages.error(request, f'Error joining game: {str(e)}')
    
    # GET request - show join form
    # Get logged-in user's codename from session
    session_codename = CodenameSessionManager.get_logged_in_codename(request)
    
    # Auto-detect logged-in player for dual binding (like Create Game)
    auto_selected_player = None
    if session_codename:
        try:
            # Find player by codename
            player_codename = PlayerCodename.objects.get(codename=session_codename)
            auto_selected_player = player_codename.player
        except PlayerCodename.DoesNotExist:
            # If no exact codename match, try to find by name similarity
            try:
                auto_selected_player = Player.objects.get(name__iexact=session_codename)
            except Player.DoesNotExist:
                pass
    
    # Get all players for search functionality
    all_players = Player.objects.all().select_related('team')
    players_json = json.dumps([{
        'name': player.name,
        'team': player.team.name if player.team else 'No Team'
    } for player in all_players])
    
    context = {
        'team_name': request.session.get('team_name', 'Guest'),
        'players_json': players_json,
        'session_codename': session_codename,
        'auto_selected_player': auto_selected_player,
    }
    
    return render(request, 'friendly_games/join_game.html', context)



def start_match(request, game_id):
    """
    Start a friendly game match - transition from WAITING_FOR_PLAYERS to ACTIVE
    """
    game = get_object_or_404(FriendlyGame, id=game_id)
    
    # Check if game is in the correct state to start
    if game.status != 'WAITING_FOR_PLAYERS':
        messages.error(request, f'Cannot start match. Game status is: {game.get_status_display()}')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    # Check if we have at least one player per team
    black_team_count = game.players.filter(team='BLACK').count()
    white_team_count = game.players.filter(team='WHITE').count()
    
    if black_team_count == 0:
        messages.error(request, 'Cannot start match: Black team has no players.')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    if white_team_count == 0:
        messages.error(request, 'Cannot start match: White team has no players.')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    # Start the match
    game.status = 'ACTIVE'
    game.started_at = timezone.now()
    game.save()
    
    # Update validation status based on codename usage
    game.update_validation_status()
    
    messages.success(request, f'Match started! Black: {black_team_count} vs White: {white_team_count}')
    return redirect('friendly_games:game_detail', game_id=game.id)


def submit_score(request, game_id):
    """
    Submit final score for a friendly game with tournament-style sequential validation
    """
    from .models import FriendlyGameResult
    
    game = get_object_or_404(FriendlyGame, id=game_id)
    
    # Check if game is in the correct state for score submission
    if game.status != 'ACTIVE':
        messages.error(request, f'Cannot submit score. Game status is: {game.get_status_display()}')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    # Check if result already exists
    try:
        existing_result = game.result
        messages.info(request, 'Score already submitted. Waiting for validation by the other team.')
        return redirect('friendly_games:game_detail', game_id=game.id)
    except FriendlyGameResult.DoesNotExist:
        pass  # No existing result, continue
    
    if request.method == 'GET':
        # Show score submission form
        context = {
            'game': game,
            'players': game.players.all(),
            'black_players': game.players.filter(team='BLACK'),
            'white_players': game.players.filter(team='WHITE'),
        }
        return render(request, 'friendly_games/submit_score.html', context)
    
    elif request.method == 'POST':
        # Process score submission
        try:
            black_score = int(request.POST.get('black_score', 0))
            white_score = int(request.POST.get('white_score', 0))
            submitting_team = request.POST.get('submitting_team')  # BLACK or WHITE
            submitter_codename = request.POST.get('submitter_codename', '').strip()
            
            # Validate scores
            if black_score < 0 or white_score < 0:
                messages.error(request, 'Scores cannot be negative.')
                return redirect('friendly_games:submit_score', game_id=game.id)
            
            # Add maximum score validation (like tournament matches)
            if black_score > 13 or white_score > 13:
                messages.error(request, 'Scores cannot exceed 13 points.')
                return redirect('friendly_games:submit_score', game_id=game.id)
            
            if black_score == white_score:
                messages.error(request, 'Scores cannot be tied. One team must win.')
                return redirect('friendly_games:submit_score', game_id=game.id)
            
            # Validate submitting team
            if submitting_team not in ['BLACK', 'WHITE']:
                messages.error(request, 'Please select which team is submitting the score.')
                return redirect('friendly_games:submit_score', game_id=game.id)
            
            # Verify submitter codename if provided
            submitter_verified = False
            if submitter_codename:
                try:
                    # Find players from the submitting team
                    submitting_players = game.players.filter(team=submitting_team)
                    for game_player in submitting_players:
                        try:
                            player_codename = game_player.player.codename_profile
                            if player_codename.codename == submitter_codename:
                                submitter_verified = True
                                # Mark the game player as verified
                                game_player.codename_verified = True
                                game_player.provided_codename = submitter_codename
                                game_player.save()
                                break
                        except PlayerCodename.DoesNotExist:
                            continue
                except Exception:
                    pass
            
            # Update game with scores but don't complete yet
            game.black_team_score = black_score
            game.white_team_score = white_score
            game.save()
            
            # Create result record for validation
            result = FriendlyGameResult.objects.create(
                game=game,
                submitted_by_team=submitting_team,
                submitter_codename=submitter_codename,
                submitter_verified=submitter_verified
            )
            
            # Determine other team for validation
            other_team = 'WHITE' if submitting_team == 'BLACK' else 'BLACK'
            
            # Success message
            verification_msg = " (Your codename was verified)" if submitter_verified else " (Codename not verified)" if submitter_codename else ""
            messages.success(request, 
                f'Score submitted by {submitting_team.title()} team! Final: Black {black_score} - White {white_score}{verification_msg}. '
                f'Waiting for {other_team.title()} team to validate the result.'
            )
            
            return redirect('friendly_games:game_detail', game_id=game.id)
            
        except ValueError:
            messages.error(request, 'Invalid score values.')
            return redirect('friendly_games:submit_score', game_id=game.id)
    
    return redirect('friendly_games:game_detail', game_id=game.id)



def validate_result(request, game_id):
    """
    Validate a submitted result - second step of sequential validation process
    """
    from .models import FriendlyGameResult
    
    game = get_object_or_404(FriendlyGame, id=game_id)
    
    # Check if there's a result to validate
    try:
        result = game.result
    except FriendlyGameResult.DoesNotExist:
        messages.error(request, 'No result has been submitted for this game.')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    # Check if result is already validated
    if not result.is_pending_validation():
        messages.info(request, 'This result has already been validated.')
        return redirect('friendly_games:game_detail', game_id=game.id)
    
    # Determine which team should validate
    validating_team = result.get_other_team()
    
    if request.method == 'GET':
        # Get logged-in user's codename from session
        session_codename = CodenameSessionManager.get_logged_in_codename(request)
        
        # Show validation form
        context = {
            'game': game,
            'result': result,
            'validating_team': validating_team,
            'validating_players': game.players.filter(team=validating_team),
            'submitted_by_team': result.submitted_by_team,
            'session_codename': session_codename,
        }
        return render(request, 'friendly_games/validate_result.html', context)
    
    elif request.method == 'POST':
        # Process validation
        try:
            validation_action = request.POST.get('validation_action')  # 'agree' or 'disagree'
            validator_codename = request.POST.get('validator_codename', '').strip()
            
            # Validate action
            if validation_action not in ['agree', 'disagree']:
                messages.error(request, 'Please select whether you agree or disagree with the result.')
                return redirect('friendly_games:validate_result', game_id=game.id)
            
            # Process the validation
            result.validate_result(validating_team, validation_action, validator_codename)
            
            # Success message based on action
            verification_msg = " (Your codename was verified)" if result.validator_verified else " (Codename not verified)" if validator_codename else ""
            
            if validation_action == 'agree':
                messages.success(request, 
                    f'{validating_team.title()} team agreed with the result! '
                    f'Game completed: Black {game.black_team_score} - White {game.white_team_score}{verification_msg}'
                )
            else:
                messages.warning(request, 
                    f'{validating_team.title()} team disagreed with the result{verification_msg}. '
                    f'The game remains active for re-submission.'
                )
            
            return redirect('friendly_games:game_detail', game_id=game.id)
            
        except Exception as e:
            messages.error(request, f'Error processing validation: {str(e)}')
            return redirect('friendly_games:validate_result', game_id=game.id)
    
    return redirect('friendly_games:game_detail', game_id=game.id)





