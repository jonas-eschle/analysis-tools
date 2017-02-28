/*****************************************************************************
 * Project: RooFit                                                           *
 *                                                                           *
 * This code was autogenerated by RooClassFactory                            *
 *****************************************************************************/

// Your description goes here...

#include "Riostream.h"

#include "BifurcatedCB.h"
#include "RooAbsReal.h"
#include "RooAbsCategory.h"
#include <math.h>
#include "TMath.h"
#include "RooMath.h"

ClassImp(BifurcatedCB)

 BifurcatedCB::BifurcatedCB(const char *name, const char *title,
                        RooAbsReal& _m,
                        RooAbsReal& _mu,
                        RooAbsReal& _sigma,
                        RooAbsReal& _alphaL,
                        RooAbsReal& _nL,
                        RooAbsReal& _alphaR,
                        RooAbsReal& _nR) :
   RooAbsPdf(name,title),
   m("m","m",this,_m),
   mu("mu","mu",this,_mu),
   sigma("sigma","sigma",this,_sigma),
   alphaL("alphaL","alphaL",this,_alphaL),
   nL("nL","nL",this,_nL),
   alphaR("alphaR","alphaR",this,_alphaR),
   nR("nR","nR",this,_nR)
 {
 }


 BifurcatedCB::BifurcatedCB(const BifurcatedCB& other, const char* name) :
   RooAbsPdf(other,name),
   m("m",this,other.m),
   mu("mu",this,other.mu),
   sigma("sigma",this,other.sigma),
   alphaL("alphaL",this,other.alphaL),
   nL("nL",this,other.nL),
   alphaR("alphaR",this,other.alphaR),
   nR("nR",this,other.nR)
 {
 }

Double_t BifurcatedCB::ApproxErf(Double_t arg) const
{
   static const double erflim = 5.0 ;
   if( arg > erflim )  return 1.0 ;
   if( arg < -erflim ) return -1.0 ;

   return RooMath::erf(arg) ;
}


 Double_t BifurcatedCB::evaluate() const
 {
   double t = (m-mu)/sigma ;
   double absAlphaL = fabs(alphaL) ;
   double absAlphaR = fabs(alphaR) ;
   double result = 0.0 ;
   // Left side
   if ( t <= -absAlphaL )
   {
      double a = std::pow(nL/absAlphaL, nL) * std::exp(-0.5*absAlphaL*absAlphaL) ;
      double b = nL/absAlphaL - absAlphaL ;
      result = a/std::pow(b-t, nL) ;
   }
   // Right side
   else if ( t >= fabs(alphaR) )
   {
      double a = std::pow(nR/absAlphaR, nR) * std::exp(-0.5*absAlphaR*absAlphaR) ;
      double b = nR/absAlphaR - absAlphaR ;
      result = a/std::pow(b+t, nR) ;
   }
   // Gaussian center
   else
   {
      result = std::exp(-0.5*t*t) ;
   }
   return result ;
 }

Int_t BifurcatedCB::getAnalyticalIntegral(RooArgSet& allVars, RooArgSet& analVars, const char* /*rangeName*/) const
{
   if( matchArgs(allVars,analVars,m) ) return 1 ;
   return 0 ;
}

Double_t BifurcatedCB::analyticalIntegral(Int_t code, const char* rangeName) const
{
   static const double sqrtPiOver2 = 1.2533141373 ;
   static const double sqrt2 = 1.4142135624 ;

   assert( code==1 ) ;
   double result = 0.0 ;
   bool useLogL = false ;
   bool useLogR = false ;


   if( fabs(nL-1.0) < 1.0e-05 ) useLogL = true;

   if( fabs(nR-1.0) < 1.0e-05 ) useLogR = true;


   double sig = fabs((Double_t) sigma) ;

   double tmin = (m.min(rangeName)-mu)/sig ;
   double tmax = (m.max(rangeName)-mu)/sig ;

   double absAlphaL = fabs((Double_t) alphaL) ;
   double absAlphaR = fabs((Double_t) alphaR) ;
   // Integrate depending on tmin and tmax
   if ( tmin <= -absAlphaL ) // Tmin is in the left tail
   {
      double a = std::pow(nL/absAlphaL, nL)*std::exp(-0.5*absAlphaL*absAlphaL) ;
      double b = nL/absAlphaL - absAlphaL ;
      if ( tmax <= -absAlphaL ) // All range included in left tail
      {
          if (useLogL) return a * sig * ( std::log(b-tmin) - std::log(b-tmax) ) ;
          else         return a*sig/(1.0-nL) * (1.0/std::pow(b-tmin, nL-1.0) - 1.0/std::pow(b-tmax, nL-1.0)) ;
      }
      else if ( tmax > -absAlphaL && tmax <= absAlphaR )
      {
          // Range extends further than left tail, so integrate it all
          if (useLogL) result = a * sig * ( std::log(b-tmin) - std::log(nL/absAlphaL) ) ;
          else         result = a*sig/(1.0-nL) * (1.0/std::pow(b-tmin, nL-1.0) - 1.0/std::pow(nL/absAlphaL, nL-1.0)) ;
          // And now the Gaussian part
          return (result + sig*sqrtPiOver2*(ApproxErf(tmax/sqrt2) - ApproxErf(-absAlphaL/sqrt2))) ;
      }
      else // We need to integrate the full gaussian part
      {
          // Range extends further than left tail, so integrate it all
          if (useLogL) result = a * sig * ( std::log(b-tmin) - std::log(nL/absAlphaL) ) ;
          else         result = a*sig/(1.0-nL) * (1.0/std::pow(b-tmin, nL-1.0) - 1.0/std::pow(nL/absAlphaL, nL-1.0)) ;
          // And now the Gaussian part
          result += sig*sqrtPiOver2*(ApproxErf(absAlphaR/sqrt2) - ApproxErf(-absAlphaL/sqrt2)) ;
          // Finally, the right tail
          double aR = std::pow(nR/absAlphaR, nR)*std::exp(-0.5*absAlphaR*absAlphaR) ;
          double bR = nR/absAlphaR - absAlphaR ;
          if (useLogR) return (result + aR*sig*( log(bR+tmax) - log(nR/absAlphaR) )) ;
          else         return (result + aR*sig/(1.0-nR)*(1.0/std::pow(bR+tmax, nR-1.0)-1.0/std::pow(nR/absAlphaR, nR-1.0))) ;
      }
   }
   else if ( tmin > -absAlphaL && tmin <= absAlphaR ) // Tmin is in the Gaussian part
   {
      if ( tmax <= absAlphaR ) // Tmax also in the Gaussian part
      {
          return sig*sqrtPiOver2*(ApproxErf(tmax/sqrt2) - ApproxErf(tmin/sqrt2)) ;
      }
      else
      {
          // Tmax in the right tail, integrate the full Gaussian part
          result = sig*sqrtPiOver2*(ApproxErf(absAlphaR/sqrt2)-ApproxErf(tmin/sqrt2)) ;
          // Finally, the right tail
          double aR = std::pow(nL/absAlphaR, nR)*std::exp(-0.5*absAlphaR*absAlphaR) ;
          double bR = nR/absAlphaR - absAlphaR ;
          if (useLogR) return (result + aR*sig*( log(bR+tmax) - log(nR/absAlphaR) )) ;
          else         return (result + aR*sig/(1.0-nR)*(1.0/std::pow(bR+tmax, nR-1.0)-1.0/std::pow(nR/absAlphaR, nR-1.0))) ;

      }
   }
   else // Tmin is in the right tail
   {
      double a = std::pow(nL/absAlphaR, nR)*std::exp(-0.5*absAlphaR*absAlphaR) ;
      double b = nR/absAlphaR - absAlphaR ;
      if (useLogR) return a*sig*( log(b+tmax) - log(nR/absAlphaR) ) ;
      else         return a*sig/(1.0-nR)*(1.0/std::pow(b+tmax, nR-1.0)-1.0/std::pow(nR/absAlphaR, nR-1.0)) ;
   }

   return result ;
}



